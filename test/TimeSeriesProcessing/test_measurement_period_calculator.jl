using Test
using Dates
using DataFrames
using Random
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, TimeRange
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.TimeSeriesProcessing.MeasurementPeriodCalculator:
    calculate_max_allowed_end_time,
    get_highest_windspeed_column,
    calculate_dataset_daily_scores,
    calculate_daily_coverage_scores,
    find_optimal_year_range,
    calculate_optimal_measurement_period,
    DailyScore

function create_mock_timeseries(
    start_time::DateTime,
    end_time::DateTime,
    interval::Period,
    ws_height::Float64,
    coverage_ratio::Float64 = 1.0
)::TimeSeriesData
    timestamps = collect(start_time:interval:end_time)
    n_points = length(timestamps)

    if coverage_ratio < 1.0
        n_keep = floor(Int, n_points * coverage_ratio)
        keep_indices = sort(randperm(n_points)[1:n_keep])
        timestamps = timestamps[keep_indices]
        n_points = length(timestamps)
    end

    wind_speeds = Vector{Union{Missing, Float64}}(rand(5.0:0.1:15.0, n_points))

    df = DataFrame(
        timestamp = timestamps,
        ws = wind_speeds
    )

    sensors = [SensorColumn(columnName=:ws, sensorType="WindSpeed", statType="avg", height=ws_height, unit="m/s", sensorDirection="N")]
    return TimeSeriesData(df, sensors)
end

function verify_exact_year_period(time_range::TimeRange)::Bool
    return time_range.max == time_range.min + Year(1) - Second(1)
end

function verify_month_aligned_start(time_range::TimeRange)::Bool
    return day(time_range.min) == 1 && hour(time_range.min) == 0 &&
           minute(time_range.min) == 0 && second(time_range.min) == 0
end

function count_days_in_range(time_range::TimeRange)::Int
    return (Date(time_range.max) - Date(time_range.min)).value + 1
end

@testset "MeasurementPeriodCalculator" begin

    @testset "Helper Functions" begin

        @testset "calculate_max_allowed_end_time" begin
            @testset "Valid meso data with 1-hour intervals" begin
                meso_last_time = DateTime(2024, 8, 31, 23, 0, 0)
                meso_ts = create_mock_timeseries(
                    DateTime(2024, 1, 1, 0, 0, 0),
                    meso_last_time,
                    Hour(1),
                    100.0
                )

                max_end = calculate_max_allowed_end_time(meso_ts)
                expected = DateTime(2024, 8, 31, 23, 59, 59)
                @test max_end == expected
            end

            @testset "Valid meso data with 10-minute intervals" begin
                meso_last_time = DateTime(2024, 8, 31, 23, 50, 0)
                meso_ts = create_mock_timeseries(
                    DateTime(2024, 8, 31, 0, 0, 0),
                    meso_last_time,
                    Minute(10),
                    100.0
                )

                max_end = calculate_max_allowed_end_time(meso_ts)
                expected = DateTime(2024, 8, 31, 23, 59, 59)
                @test max_end == expected
            end

            @testset "Empty timestamps throws error" begin
                df = DataFrame(timestamp = DateTime[], ws = Float64[])
                sensors = [SensorColumn(columnName=:ws, sensorType="WindSpeed", statType="avg", height=100.0, unit="m/s", sensorDirection="N")]
                meso_ts = TimeSeriesData(df, sensors)

                @test_throws ErrorException calculate_max_allowed_end_time(meso_ts)
            end

            @testset "Single timestamp" begin
                single_time = DateTime(2024, 8, 31, 23, 0, 0)
                df = DataFrame(timestamp = [single_time], ws = [10.0])
                sensors = [SensorColumn(columnName=:ws, sensorType="WindSpeed", statType="avg", height=100.0, unit="m/s", sensorDirection="N")]
                meso_ts = TimeSeriesData(df, sensors)

                max_end = calculate_max_allowed_end_time(meso_ts)
                expected = DateTime(2024, 8, 31, 23, 9, 59)
                @test max_end == expected
            end
        end

        @testset "get_highest_windspeed_column" begin
            @testset "Multiple WS sensors at different heights" begin
                df = DataFrame(
                    timestamp = [DateTime(2024, 1, 1)],
                    ws_10m = [5.0],
                    ws_50m = [8.0],
                    ws_120m = [10.0]
                )
                sensors = [
                    SensorColumn(columnName=:ws_10m, sensorType="WindSpeed", statType="avg", height=10.0, unit="m/s", sensorDirection="N"),
                    SensorColumn(columnName=:ws_50m, sensorType="WindSpeed", statType="avg", height=50.0, unit="m/s", sensorDirection="N"),
                    SensorColumn(columnName=:ws_120m, sensorType="WindSpeed", statType="avg", height=120.0, unit="m/s", sensorDirection="N")
                ]
                ts_data = TimeSeriesData(df, sensors)

                highest_col = get_highest_windspeed_column(ts_data)
                @test highest_col == :ws_120m
            end

            @testset "Single WS sensor" begin
                df = DataFrame(timestamp = [DateTime(2024, 1, 1)], ws_80m = [9.0])
                sensors = [SensorColumn(columnName=:ws_80m, sensorType="WindSpeed", statType="avg", height=80.0, unit="m/s", sensorDirection="N")]
                ts_data = TimeSeriesData(df, sensors)

                highest_col = get_highest_windspeed_column(ts_data)
                @test highest_col == :ws_80m
            end

            @testset "No WS sensors throws error" begin
                df = DataFrame(
                    timestamp = [DateTime(2024, 1, 1)],
                    temp = [20.0],
                    pressure = [1013.0]
                )
                sensors = [
                    SensorColumn(columnName=:temp, sensorType="Temperature", statType="avg", height=10.0, unit="C", sensorDirection="N"),
                    SensorColumn(columnName=:pressure, sensorType="Pressure", statType="avg", height=10.0, unit="hPa", sensorDirection="N")
                ]
                ts_data = TimeSeriesData(df, sensors)

                @test_throws ErrorException get_highest_windspeed_column(ts_data)
            end

            @testset "Mixed statTypes - only considers avg" begin
                df = DataFrame(
                    timestamp = [DateTime(2024, 1, 1)],
                    ws_avg = [10.0],
                    ws_max = [15.0],
                    ws_min = [5.0]
                )
                sensors = [
                    SensorColumn(columnName=:ws_avg, sensorType="WindSpeed", statType="avg", height=100.0, unit="m/s", sensorDirection="N"),
                    SensorColumn(columnName=:ws_max, sensorType="WindSpeed", statType="max", height=100.0, unit="m/s", sensorDirection="N"),
                    SensorColumn(columnName=:ws_min, sensorType="WindSpeed", statType="min", height=100.0, unit="m/s", sensorDirection="N")
                ]
                ts_data = TimeSeriesData(df, sensors)

                highest_col = get_highest_windspeed_column(ts_data)
                @test highest_col == :ws_avg
            end
        end

        @testset "calculate_dataset_daily_scores" begin
            @testset "Full day with 10-minute intervals" begin
                start_time = DateTime(2024, 1, 1, 0, 0, 0)
                end_time = DateTime(2024, 1, 1, 23, 50, 0)
                ts_data = create_mock_timeseries(start_time, end_time, Minute(10), 80.0, 1.0)
                max_end_date = Date(2024, 12, 31)

                daily_scores = calculate_dataset_daily_scores(ts_data, :ws, 1.0, max_end_date)

                @test nrow(daily_scores) == 1
                @test daily_scores[1, :day] == Date(2024, 1, 1)
                @test daily_scores[1, :daily_score] ≈ 24.0
            end

            @testset "Half day coverage" begin
                start_time = DateTime(2024, 1, 1, 0, 0, 0)
                end_time = DateTime(2024, 1, 1, 23, 50, 0)
                ts_data = create_mock_timeseries(start_time, end_time, Minute(10), 80.0, 0.5)
                max_end_date = Date(2024, 12, 31)

                daily_scores = calculate_dataset_daily_scores(ts_data, :ws, 1.0, max_end_date)

                @test nrow(daily_scores) == 1
                @test daily_scores[1, :daily_score] ≈ 12.0 atol=1.0
            end

            @testset "Weight factor application" begin
                start_time = DateTime(2024, 1, 1, 0, 0, 0)
                end_time = DateTime(2024, 1, 1, 23, 50, 0)
                ts_data = create_mock_timeseries(start_time, end_time, Minute(10), 80.0, 1.0)
                max_end_date = Date(2024, 12, 31)

                daily_scores = calculate_dataset_daily_scores(ts_data, :ws, 0.5, max_end_date)

                @test nrow(daily_scores) == 1
                @test daily_scores[1, :daily_score] ≈ 12.0
            end

            @testset "Missing WS column returns empty DataFrame" begin
                df = DataFrame(timestamp = [DateTime(2024, 1, 1)], temp = [20.0])
                sensors = [SensorColumn(columnName=:temp, sensorType="Temperature", statType="avg", height=10.0, unit="C", sensorDirection="N")]
                ts_data = TimeSeriesData(df, sensors)
                max_end_date = Date(2024, 12, 31)

                daily_scores = calculate_dataset_daily_scores(ts_data, :ws, 1.0, max_end_date)

                @test nrow(daily_scores) == 0
            end

            @testset "Data beyond max_end_date filtered out" begin
                start_time = DateTime(2024, 1, 1, 0, 0, 0)
                end_time = DateTime(2024, 1, 2, 23, 50, 0)
                ts_data = create_mock_timeseries(start_time, end_time, Minute(10), 80.0, 1.0)
                max_end_date = Date(2024, 1, 1)

                daily_scores = calculate_dataset_daily_scores(ts_data, :ws, 1.0, max_end_date)

                @test nrow(daily_scores) == 1
                @test daily_scores[1, :day] == Date(2024, 1, 1)
            end

            @testset "Score capping at 24 * weight" begin
                timestamps = vcat(
                    collect(DateTime(2024, 1, 1, 0, 0, 0):Minute(10):DateTime(2024, 1, 1, 23, 50, 0)),
                    collect(DateTime(2024, 1, 1, 0, 0, 0):Minute(5):DateTime(2024, 1, 1, 23, 55, 0))
                )
                wind_speeds = Vector{Union{Missing, Float64}}(rand(5.0:0.1:15.0, length(timestamps)))
                df = DataFrame(timestamp = timestamps, ws = wind_speeds)
                sensors = [SensorColumn(columnName=:ws, sensorType="WindSpeed", statType="avg", height=80.0, unit="m/s", sensorDirection="N")]
                ts_data = TimeSeriesData(df, sensors)
                max_end_date = Date(2024, 12, 31)

                daily_scores = calculate_dataset_daily_scores(ts_data, :ws, 1.0, max_end_date)

                @test daily_scores[1, :daily_score] <= 24.0
            end
        end
    end

    @testset "Daily Coverage Scoring" begin
        @testset "calculate_daily_coverage_scores" begin
            @testset "Both single and cross full coverage" begin
                start_time = DateTime(2024, 1, 1, 0, 0, 0)
                end_time = DateTime(2024, 1, 2, 23, 50, 0)
                max_end_time = DateTime(2024, 12, 31, 23, 59, 59)

                single_ts = create_mock_timeseries(start_time, end_time, Minute(10), 80.0, 1.0)
                cross_ts = create_mock_timeseries(start_time, end_time, Minute(10), 100.0, 1.0)

                daily_scores = calculate_daily_coverage_scores(single_ts, cross_ts, max_end_time, 1.0, 0.5)

                @test length(daily_scores) == 2
                @test all(ds.single_score ≈ 24.0 for ds in daily_scores)
                @test all(ds.cross_score ≈ 24.0 for ds in daily_scores)
                @test all(ds.total_score ≈ 48.0 for ds in daily_scores)
            end

            @testset "Only single data" begin
                start_time = DateTime(2024, 1, 1, 0, 0, 0)
                end_time = DateTime(2024, 1, 1, 23, 50, 0)
                max_end_time = DateTime(2024, 12, 31, 23, 59, 59)

                single_ts = create_mock_timeseries(start_time, end_time, Minute(10), 80.0, 1.0)

                df_empty = DataFrame(timestamp = DateTime[], ws = Float64[])
                sensors_empty = [SensorColumn(columnName=:ws, sensorType="WindSpeed", statType="avg", height=100.0, unit="m/s", sensorDirection="N")]
                cross_ts = TimeSeriesData(df_empty, sensors_empty)

                daily_scores = calculate_daily_coverage_scores(single_ts, cross_ts, max_end_time, 1.0, 0.5)

                @test length(daily_scores) >= 1
                @test all(ds.single_score ≥ 0.0 for ds in daily_scores)
                @test all(ds.cross_score == 0.0 for ds in daily_scores)
            end

            @testset "Scores are sorted by date" begin
                start_time = DateTime(2024, 1, 1, 0, 0, 0)
                end_time = DateTime(2024, 1, 3, 23, 50, 0)
                max_end_time = DateTime(2024, 12, 31, 23, 59, 59)

                single_ts = create_mock_timeseries(start_time, end_time, Minute(10), 80.0, 1.0)
                cross_ts = create_mock_timeseries(start_time, end_time, Minute(10), 100.0, 1.0)

                daily_scores = calculate_daily_coverage_scores(single_ts, cross_ts, max_end_time, 1.0, 0.5)

                dates = [ds.date for ds in daily_scores]
                @test issorted(dates)
            end
        end
    end

    @testset "Optimal Period Finding" begin
        @testset "find_optimal_year_range" begin
            @testset "Year(1) - Second(1) Calculation" begin
                @testset "Start 2023-08-01 → End 2024-07-31 23:59:59" begin
                    daily_scores = [DailyScore(Date(2023, 8, 1) + Day(i), 1.0, 1.0, 2.0) for i in 0:400]
                    earliest_start = Date(2023, 8, 1)
                    latest_end = Date(2024, 9, 1)

                    time_range = find_optimal_year_range(daily_scores, earliest_start, latest_end)

                    @test verify_exact_year_period(time_range)
                    @test verify_month_aligned_start(time_range)
                    @test time_range.min == DateTime(2023, 8, 1, 0, 0, 0)
                    @test time_range.max == DateTime(2024, 7, 31, 23, 59, 59)
                    @test count_days_in_range(time_range) == 366
                end

                @testset "Start 2024-01-01 → End 2024-12-31 23:59:59 (LEAP YEAR)" begin
                    daily_scores = [DailyScore(Date(2024, 1, 1) + Day(i), 1.0, 1.0, 2.0) for i in 0:400]
                    earliest_start = Date(2024, 1, 1)
                    latest_end = Date(2025, 2, 1)

                    time_range = find_optimal_year_range(daily_scores, earliest_start, latest_end)

                    @test verify_exact_year_period(time_range)
                    @test verify_month_aligned_start(time_range)
                    @test time_range.min == DateTime(2024, 1, 1, 0, 0, 0)
                    @test time_range.max == DateTime(2024, 12, 31, 23, 59, 59)
                    @test count_days_in_range(time_range) == 366

                    feb_29 = Date(2024, 2, 29)
                    @test Date(time_range.min) <= feb_29 <= Date(time_range.max)
                end

                @testset "Start 2024-02-01 → End 2025-01-31 23:59:59 (crosses leap year)" begin
                    daily_scores = [DailyScore(Date(2024, 2, 1) + Day(i), 1.0, 1.0, 2.0) for i in 0:400]
                    earliest_start = Date(2024, 2, 1)
                    latest_end = Date(2025, 3, 1)

                    time_range = find_optimal_year_range(daily_scores, earliest_start, latest_end)

                    @test verify_exact_year_period(time_range)
                    @test verify_month_aligned_start(time_range)
                    @test time_range.min == DateTime(2024, 2, 1, 0, 0, 0)
                    @test time_range.max == DateTime(2025, 1, 31, 23, 59, 59)
                    @test count_days_in_range(time_range) == 366
                end

                @testset "Mid-month start gets aligned to month start" begin
                    daily_scores = [DailyScore(Date(2023, 12, 15) + Day(i), 1.0, 1.0, 2.0) for i in 0:400]
                    earliest_start = Date(2023, 12, 15)
                    latest_end = Date(2025, 1, 1)

                    time_range = find_optimal_year_range(daily_scores, earliest_start, latest_end)

                    @test verify_exact_year_period(time_range)
                    @test verify_month_aligned_start(time_range)
                    @test time_range.min == DateTime(2023, 12, 1, 0, 0, 0)
                    @test time_range.max == DateTime(2024, 11, 30, 23, 59, 59)
                end
            end

            @testset "Month Alignment" begin
                @testset "Optimal start 2024-03-15 → Aligned 2024-03-01" begin
                    daily_scores = [DailyScore(Date(2024, 3, 15) + Day(i), 1.0, 1.0, 2.0) for i in 0:400]
                    earliest_start = Date(2024, 3, 15)
                    latest_end = Date(2025, 4, 1)

                    time_range = find_optimal_year_range(daily_scores, earliest_start, latest_end)

                    @test day(time_range.min) == 1
                    @test month(time_range.min) == 3
                    @test year(time_range.min) == 2024
                end

                @testset "Optimal start already on month start" begin
                    daily_scores = [DailyScore(Date(2024, 1, 1) + Day(i), 1.0, 1.0, 2.0) for i in 0:400]
                    earliest_start = Date(2024, 1, 1)
                    latest_end = Date(2025, 2, 1)

                    time_range = find_optimal_year_range(daily_scores, earliest_start, latest_end)

                    @test time_range.min == DateTime(2024, 1, 1, 0, 0, 0)
                end
            end

            @testset "Edge Cases" begin
                @testset "Date range < 365 days throws error" begin
                    daily_scores = [DailyScore(Date(2024, 1, 1) + Day(i), 1.0, 1.0, 2.0) for i in 0:200]
                    earliest_start = Date(2024, 1, 1)
                    latest_end = Date(2024, 7, 1)

                    @test_throws ErrorException find_optimal_year_range(daily_scores, earliest_start, latest_end)
                end

                @testset "Date range = exactly 365 days" begin
                    daily_scores = [DailyScore(Date(2023, 1, 1) + Day(i), 1.0, 1.0, 2.0) for i in 0:364]
                    earliest_start = Date(2023, 1, 1)
                    latest_end = Date(2023, 12, 31)

                    time_range = find_optimal_year_range(daily_scores, earliest_start, latest_end)

                    @test verify_exact_year_period(time_range)
                    @test count_days_in_range(time_range) == 365
                end

                @testset "All zero scores still returns valid TimeRange" begin
                    daily_scores = [DailyScore(Date(2024, 1, 1) + Day(i), 0.0, 0.0, 0.0) for i in 0:400]
                    earliest_start = Date(2024, 1, 1)
                    latest_end = Date(2025, 2, 1)

                    time_range = find_optimal_year_range(daily_scores, earliest_start, latest_end)

                    @test verify_exact_year_period(time_range)
                end

                @testset "Best period at start of range" begin
                    daily_scores = vcat(
                        [DailyScore(Date(2024, 1, 1) + Day(i), 1.0, 1.0, 2.0) for i in 0:364],
                        [DailyScore(Date(2024, 12, 31) + Day(i), 0.5, 0.5, 1.0) for i in 1:100]
                    )
                    earliest_start = Date(2024, 1, 1)
                    latest_end = Date(2025, 4, 10)

                    time_range = find_optimal_year_range(daily_scores, earliest_start, latest_end)

                    @test time_range.min == DateTime(2024, 1, 1, 0, 0, 0)
                end

                @testset "Best period in middle" begin
                    daily_scores = vcat(
                        [DailyScore(Date(2023, 1, 1) + Day(i), 0.5, 0.5, 1.0) for i in 0:180],
                        [DailyScore(Date(2023, 7, 1) + Day(i), 1.0, 1.0, 2.0) for i in 0:364],
                        [DailyScore(Date(2024, 6, 30) + Day(i), 0.5, 0.5, 1.0) for i in 1:100]
                    )
                    earliest_start = Date(2023, 1, 1)
                    latest_end = Date(2024, 10, 10)

                    time_range = find_optimal_year_range(daily_scores, earliest_start, latest_end)

                    @test time_range.min == DateTime(2023, 7, 1, 0, 0, 0)
                end
            end

            @testset "Scoring Logic" begin
                @testset "Period with highest total_score selected" begin
                    daily_scores = vcat(
                        [DailyScore(Date(2023, 1, 1) + Day(i), 0.3, 0.3, 0.6) for i in 0:200],
                        [DailyScore(Date(2023, 7, 20) + Day(i), 0.9, 0.9, 1.8) for i in 0:364],
                        [DailyScore(Date(2024, 7, 19) + Day(i), 0.3, 0.3, 0.6) for i in 1:100]
                    )
                    earliest_start = Date(2023, 1, 1)
                    latest_end = Date(2024, 10, 27)

                    time_range = find_optimal_year_range(daily_scores, earliest_start, latest_end)

                    @test month(time_range.min) == 7
                    @test year(time_range.min) == 2023
                end
            end
        end
    end

    @testset "Integration Tests" begin
        @testset "calculate_optimal_measurement_period" begin
            @testset "Basic scenario with all datasets" begin
                single_ts = create_mock_timeseries(
                    DateTime(2023, 1, 1, 0, 0, 0),
                    DateTime(2024, 12, 31, 23, 50, 0),
                    Minute(10),
                    80.0,
                    0.9
                )

                cross_ts = create_mock_timeseries(
                    DateTime(2023, 7, 1, 0, 0, 0),
                    DateTime(2024, 8, 31, 23, 50, 0),
                    Minute(10),
                    100.0,
                    0.8
                )

                meso_ts = create_mock_timeseries(
                    DateTime(2023, 1, 1, 0, 0, 0),
                    DateTime(2024, 12, 31, 23, 0, 0),
                    Hour(1),
                    100.0,
                    1.0
                )

                time_range = calculate_optimal_measurement_period(single_ts, cross_ts, meso_ts)

                @test verify_exact_year_period(time_range)
                @test verify_month_aligned_start(time_range)

                meso_max_end = calculate_max_allowed_end_time(meso_ts)
                @test time_range.max <= meso_max_end

                cross_start = minimum(filter(!ismissing, cross_ts.df.timestamp))
                @test time_range.min >= DateTime(Date(cross_start))
            end

            @testset "Year(1) - Second(1) End-to-End verification" begin
                single_ts = create_mock_timeseries(
                    DateTime(2023, 1, 1, 0, 0, 0),
                    DateTime(2024, 12, 31, 23, 50, 0),
                    Minute(10),
                    80.0,
                    1.0
                )

                cross_ts = create_mock_timeseries(
                    DateTime(2023, 7, 1, 0, 0, 0),
                    DateTime(2024, 8, 31, 23, 50, 0),
                    Minute(10),
                    100.0,
                    1.0
                )

                meso_ts = create_mock_timeseries(
                    DateTime(2023, 1, 1, 0, 0, 0),
                    DateTime(2024, 12, 31, 23, 0, 0),
                    Hour(1),
                    100.0,
                    1.0
                )

                time_range = calculate_optimal_measurement_period(single_ts, cross_ts, meso_ts)

                duration_days = count_days_in_range(time_range)
                @test duration_days ∈ [365, 366]

                if isleapyear(year(time_range.min))
                    feb_29 = Date(year(time_range.min), 2, 29)
                    if Date(time_range.min) <= feb_29 <= Date(time_range.max)
                        @test duration_days == 366
                    end
                end
            end
        end
    end

    @testset "Regression Tests" begin
        @testset "Month Alignment Bug Prevention" begin
            @testset "Prevent 396-day period bug" begin
                daily_scores = [DailyScore(Date(2023, 8, 1) + Day(i), 1.0, 1.0, 2.0) for i in 0:400]
                earliest_start = Date(2023, 8, 1)
                latest_end = Date(2024, 9, 15)

                time_range = find_optimal_year_range(daily_scores, earliest_start, latest_end)

                @test time_range.min == DateTime(2023, 8, 1, 0, 0, 0)
                @test time_range.max == DateTime(2024, 7, 31, 23, 59, 59)

                duration_days = count_days_in_range(time_range)
                @test duration_days == 366
                @test duration_days != 396
            end

            @testset "Verify exact Year(1) - Second(1) formula" begin
                test_cases = [
                    (Date(2023, 1, 1), DateTime(2023, 12, 31, 23, 59, 59)),
                    (Date(2023, 8, 1), DateTime(2024, 7, 31, 23, 59, 59)),
                    (Date(2024, 1, 1), DateTime(2024, 12, 31, 23, 59, 59)),
                    (Date(2024, 2, 1), DateTime(2025, 1, 31, 23, 59, 59))
                ]

                for (start_date, expected_end) in test_cases
                    daily_scores = [DailyScore(start_date + Day(i), 1.0, 1.0, 2.0) for i in 0:400]
                    earliest_start = start_date
                    latest_end = start_date + Day(400)

                    time_range = find_optimal_year_range(daily_scores, earliest_start, latest_end)

                    @test time_range.min == DateTime(start_date)
                    @test time_range.max == expected_end
                    @test verify_exact_year_period(time_range)
                end
            end
        end
    end
end
