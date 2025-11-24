using Test
using Dates
using DataFrames
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, TimeRange
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.TimeSeriesProcessing.MastPeriodAlignment:
    calculate_pairwise_overlap,
    calculate_pairwise_intersection_days,
    calculate_relative_overlap_matrix,
    calculate_absolute_overlap_matrix,
    cluster_masts_by_overlap,
    determine_target_period_years,
    calculate_union_time_range,
    score_cluster_window,
    calculate_cluster_optimal_period

function create_mock_timeseries(
    start_time::DateTime,
    end_time::DateTime,
    interval::Period,
    ws_height::Float64
)::TimeSeriesData
    timestamps = collect(start_time:interval:end_time)
    n_points = length(timestamps)
    wind_speeds = Vector{Union{Missing, Float64}}(rand(5.0:0.1:15.0, n_points))

    df = DataFrame(
        timestamp = timestamps,
        ws = wind_speeds
    )

    sensors = [SensorColumn(columnName=:ws, sensorType="WindSpeed", statType="avg", height=ws_height, unit="m/s", sensorDirection="N")]
    return TimeSeriesData(df, sensors)
end

@testset "MastPeriodAlignment" begin

    @testset "calculate_pairwise_intersection_days" begin
        using CleanMastProject.TimeSeriesProcessing.MastPeriodAlignment: extract_valid_timestamps
        using CleanMastProject.TimeSeriesProcessing.IntervalDetection: get_interval_statistics

        @testset "Two masts with full overlap" begin
            # Create two masts with identical timestamp range
            ts1 = create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 80.0)
            ts2 = create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 100.0)

            mast_names = ["M01", "M02"]
            valid_timestamps = Dict(
                "M01" => extract_valid_timestamps(ts1),
                "M02" => extract_valid_timestamps(ts2)
            )
            intervals = Dict(
                "M01" => Dates.value(Millisecond(get_interval_statistics(ts1).representative_interval)) / (1000.0 * 3600.0),
                "M02" => Dates.value(Millisecond(get_interval_statistics(ts2).representative_interval)) / (1000.0 * 3600.0)
            )

            intersection_days, period_days = calculate_pairwise_intersection_days(valid_timestamps, intervals, mast_names)

            # Check matrix structure
            @test size(intersection_days) == (2, 2)
            @test length(period_days) == 2

            # Self-intersection equals period
            @test intersection_days[1, 1] == period_days[1]
            @test intersection_days[2, 2] == period_days[2]

            # Full overlap: intersection should equal both periods (approximately)
            @test intersection_days[1, 2] ≈ period_days[1] atol=1.0
            @test intersection_days[1, 2] ≈ period_days[2] atol=1.0

            # Symmetry
            @test intersection_days[1, 2] == intersection_days[2, 1]

            # Period length should be ~365 days
            @test period_days[1] ≈ 365.0 atol=2.0
            @test period_days[2] ≈ 365.0 atol=2.0
        end

        @testset "Two masts with partial overlap" begin
            # M01: Jan-Dec 2023 (12 months)
            # M02: Sep 2023 - Aug 2024 (12 months, 4 months overlap)
            ts1 = create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 80.0)
            ts2 = create_mock_timeseries(DateTime(2023, 9, 1), DateTime(2024, 8, 31, 23, 50, 0), Minute(10), 100.0)

            mast_names = ["M01", "M02"]
            valid_timestamps = Dict(
                "M01" => extract_valid_timestamps(ts1),
                "M02" => extract_valid_timestamps(ts2)
            )
            intervals = Dict(
                "M01" => Dates.value(Millisecond(get_interval_statistics(ts1).representative_interval)) / (1000.0 * 3600.0),
                "M02" => Dates.value(Millisecond(get_interval_statistics(ts2).representative_interval)) / (1000.0 * 3600.0)
            )

            intersection_days, period_days = calculate_pairwise_intersection_days(valid_timestamps, intervals, mast_names)

            # Intersection should be ~4 months (Sep-Dec) ≈ 122 days
            @test intersection_days[1, 2] ≈ 122.0 atol=5.0
            @test intersection_days[2, 1] == intersection_days[1, 2]

            # Period lengths should be ~365 days each
            @test period_days[1] ≈ 365.0 atol=2.0
            @test period_days[2] ≈ 366.0 atol=2.0  # Sep to Aug is 366 days
        end

        @testset "Two masts with no overlap" begin
            ts1 = create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 6, 30, 23, 50, 0), Minute(10), 80.0)
            ts2 = create_mock_timeseries(DateTime(2023, 7, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 100.0)

            mast_names = ["M01", "M02"]
            valid_timestamps = Dict(
                "M01" => extract_valid_timestamps(ts1),
                "M02" => extract_valid_timestamps(ts2)
            )
            intervals = Dict(
                "M01" => Dates.value(Millisecond(get_interval_statistics(ts1).representative_interval)) / (1000.0 * 3600.0),
                "M02" => Dates.value(Millisecond(get_interval_statistics(ts2).representative_interval)) / (1000.0 * 3600.0)
            )

            intersection_days, period_days = calculate_pairwise_intersection_days(valid_timestamps, intervals, mast_names)

            # No overlap
            @test intersection_days[1, 2] == 0.0
            @test intersection_days[2, 1] == 0.0

            # Period lengths should be ~6 months each
            @test period_days[1] ≈ 181.0 atol=2.0
            @test period_days[2] ≈ 184.0 atol=2.0
        end

        @testset "Missing data reduces intersection" begin
            # Create two masts with same time range but different data completeness
            ts1 = create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 80.0)
            ts2 = create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 100.0)

            # Set first half of ts2 to missing
            mid_point = div(nrow(ts2.df), 2)
            ts2.df[1:mid_point, :ws] .= missing

            mast_names = ["M01", "M02"]
            valid_timestamps = Dict(
                "M01" => extract_valid_timestamps(ts1),
                "M02" => extract_valid_timestamps(ts2)
            )
            intervals = Dict(
                "M01" => Dates.value(Millisecond(get_interval_statistics(ts1).representative_interval)) / (1000.0 * 3600.0),
                "M02" => Dates.value(Millisecond(get_interval_statistics(ts2).representative_interval)) / (1000.0 * 3600.0)
            )

            intersection_days, period_days = calculate_pairwise_intersection_days(valid_timestamps, intervals, mast_names)

            # M01 has full year (~365 days)
            @test period_days[1] ≈ 365.0 atol=2.0

            # M02 has half year (~182.5 days)
            @test period_days[2] ≈ 182.5 atol=2.0

            # Intersection is only the valid half of M02
            @test intersection_days[1, 2] ≈ 182.5 atol=2.0
        end
    end

    @testset "calculate_relative_overlap_matrix" begin
        @testset "Full overlap (equal periods)" begin
            intersection_days = [365.0 365.0; 365.0 365.0]
            period_days = [365.0, 365.0]

            relative_matrix = calculate_relative_overlap_matrix(intersection_days, period_days)

            @test relative_matrix[1, 1] == 1.0
            @test relative_matrix[2, 2] == 1.0
            @test relative_matrix[1, 2] == 1.0  # 365 / min(365, 365) = 1.0
            @test relative_matrix[2, 1] == 1.0
        end

        @testset "Partial overlap (shorter fully within longer)" begin
            # M01: 365 days, M02: 122 days, intersection: 122 days (M02 fully within M01)
            intersection_days = [365.0 122.0; 122.0 122.0]
            period_days = [365.0, 122.0]

            relative_matrix = calculate_relative_overlap_matrix(intersection_days, period_days)

            @test relative_matrix[1, 1] == 1.0
            @test relative_matrix[2, 2] == 1.0
            @test relative_matrix[1, 2] == 1.0  # 122 / min(365, 122) = 122 / 122 = 1.0
            @test relative_matrix[2, 1] == 1.0
        end

        @testset "Partial overlap (equal periods)" begin
            # Both 365 days, intersection 122 days
            intersection_days = [365.0 122.0; 122.0 365.0]
            period_days = [365.0, 365.0]

            relative_matrix = calculate_relative_overlap_matrix(intersection_days, period_days)

            @test relative_matrix[1, 2] ≈ 122.0 / 365.0  # ≈ 0.334
            @test relative_matrix[2, 1] == relative_matrix[1, 2]
        end

        @testset "No overlap" begin
            intersection_days = [181.0 0.0; 0.0 184.0]
            period_days = [181.0, 184.0]

            relative_matrix = calculate_relative_overlap_matrix(intersection_days, period_days)

            @test relative_matrix[1, 2] == 0.0
            @test relative_matrix[2, 1] == 0.0
        end

        @testset "Three masts with varying overlaps" begin
            # M01: 365 days, M02: 365 days, M03: 184 days (last 6 months)
            # M01-M02: full overlap (365 days)
            # M01-M03: partial overlap (184 days)
            # M02-M03: partial overlap (184 days)
            intersection_days = [
                365.0 365.0 184.0;
                365.0 365.0 184.0;
                184.0 184.0 184.0
            ]
            period_days = [365.0, 365.0, 184.0]

            relative_matrix = calculate_relative_overlap_matrix(intersection_days, period_days)

            @test relative_matrix[1, 1] == 1.0
            @test relative_matrix[2, 2] == 1.0
            @test relative_matrix[3, 3] == 1.0
            @test relative_matrix[1, 2] == 1.0  # 365 / 365
            @test relative_matrix[1, 3] == 1.0  # 184 / 184 (M03 is the shorter)
            @test relative_matrix[2, 3] == 1.0  # 184 / 184
        end
    end

    @testset "calculate_absolute_overlap_matrix" begin
        @testset "Full year divided by 120-day threshold" begin
            intersection_days = [365.0 365.0; 365.0 365.0]
            threshold_period = 120

            absolute_matrix = calculate_absolute_overlap_matrix(intersection_days, threshold_period)

            @test absolute_matrix[1, 1] ≈ 365.0 / 120.0  # ≈ 3.04
            @test absolute_matrix[2, 2] ≈ 365.0 / 120.0
            @test absolute_matrix[1, 2] ≈ 365.0 / 120.0
            @test absolute_matrix[2, 1] ≈ 365.0 / 120.0
        end

        @testset "4-month overlap divided by 120-day threshold" begin
            intersection_days = [365.0 122.0; 122.0 365.0]
            threshold_period = 120

            absolute_matrix = calculate_absolute_overlap_matrix(intersection_days, threshold_period)

            @test absolute_matrix[1, 2] ≈ 122.0 / 120.0  # ≈ 1.017
            @test absolute_matrix[2, 1] ≈ 122.0 / 120.0
        end

        @testset "No overlap" begin
            intersection_days = [181.0 0.0; 0.0 184.0]
            threshold_period = 120

            absolute_matrix = calculate_absolute_overlap_matrix(intersection_days, threshold_period)

            @test absolute_matrix[1, 2] == 0.0
            @test absolute_matrix[2, 1] == 0.0
        end

        @testset "Below threshold (60 days / 120)" begin
            intersection_days = [365.0 60.0; 60.0 365.0]
            threshold_period = 120

            absolute_matrix = calculate_absolute_overlap_matrix(intersection_days, threshold_period)

            @test absolute_matrix[1, 2] == 0.5
            @test absolute_matrix[2, 1] == 0.5
        end
    end

    @testset "calculate_pairwise_overlap" begin
        @testset "Two masts with full overlap (timestamp-based)" begin
            mast_ts = Dict(
                "M01" => create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 80.0),
                "M02" => create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 100.0)
            )

            overlap_matrix = calculate_pairwise_overlap(mast_ts, 120)

            @test size(overlap_matrix) == (2, 2)
            # Self-overlap: relative=1.0, absolute=365/120≈3.04, max=3.04
            @test overlap_matrix[1, 1] ≈ 365.0 / 120.0 atol=0.1
            @test overlap_matrix[2, 2] ≈ 365.0 / 120.0 atol=0.1
            # Full overlap: all timestamps match, relative=1.0, absolute=~365/120=3.04, max=3.04
            @test overlap_matrix[1, 2] >= 1.0  # High overlap (can exceed 1.0 due to absolute criterion)
            @test overlap_matrix[2, 1] >= 1.0  # Symmetric
        end

        @testset "1-month mast fully within 12-month mast (relative wins)" begin
            mast_ts = Dict(
                "M01" => create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 80.0),
                "M02" => create_mock_timeseries(DateTime(2023, 6, 1), DateTime(2023, 6, 30, 23, 50, 0), Minute(10), 100.0)
            )

            overlap_matrix = calculate_pairwise_overlap(mast_ts, 120)

            # 30 days intersection (all of M02's timestamps)
            # relative = 30 / 30 = 1.0
            # absolute = 30 / 120 = 0.25
            # max = 1.0
            @test overlap_matrix[1, 2] ≈ 1.0
            @test overlap_matrix[2, 1] ≈ 1.0  # Symmetric
        end

        @testset "12-month + 12-month with 4-month intersection (absolute wins)" begin
            mast_ts = Dict(
                "M01" => create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 80.0),
                "M02" => create_mock_timeseries(DateTime(2023, 9, 1), DateTime(2024, 8, 31, 23, 50, 0), Minute(10), 100.0)
            )

            # Calculate intermediate matrices for debugging
            using CleanMastProject.TimeSeriesProcessing.MastPeriodAlignment: extract_valid_timestamps
            using CleanMastProject.TimeSeriesProcessing.IntervalDetection: get_interval_statistics

            mast_names = sort(collect(keys(mast_ts)))
            valid_timestamps = Dict{String, Set{DateTime}}()
            intervals = Dict{String, Float64}()
            for mast_name in mast_names
                ts = mast_ts[mast_name]
                valid_timestamps[mast_name] = extract_valid_timestamps(ts)
                stats = get_interval_statistics(ts)
                intervals[mast_name] = Dates.value(Millisecond(stats.representative_interval)) / (1000.0 * 3600.0)
            end

            intersection_days, period_days = calculate_pairwise_intersection_days(valid_timestamps, intervals, mast_names)
            relative_matrix = calculate_relative_overlap_matrix(intersection_days, period_days)
            absolute_matrix = calculate_absolute_overlap_matrix(intersection_days, 120)

            println("\n📊 DEBUG: 4-month intersection test")
            println("  Intersection days[1,2]: $(intersection_days[1,2])")
            println("  Period days: $(period_days)")
            println("  Relative matrix[1,2]: $(relative_matrix[1,2])")
            println("  Absolute matrix[1,2]: $(absolute_matrix[1,2])")
            println("  max(relative, absolute): $(max(relative_matrix[1,2], absolute_matrix[1,2]))")

            overlap_matrix = calculate_pairwise_overlap(mast_ts, 120)
            println("  Final overlap[1,2]: $(overlap_matrix[1,2])")

            # 4 months = ~122 days intersection (Sept-Dec)
            # With timestamp-based calculation:
            #   intersection timestamps ≈ 122 days worth
            #   relative = 122 / 365 ≈ 0.334
            #   absolute = 122 / 120 ≈ 1.02
            #   max(0.334, 1.02) = 1.02
            @test overlap_matrix[1, 2] >= 1.0  # absolute should win
            @test overlap_matrix[2, 1] >= 1.0
        end

        @testset "No overlap" begin
            mast_ts = Dict(
                "M01" => create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 6, 30, 23, 50, 0), Minute(10), 80.0),
                "M02" => create_mock_timeseries(DateTime(2023, 7, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 100.0)
            )

            overlap_matrix = calculate_pairwise_overlap(mast_ts, 120)

            @test overlap_matrix[1, 2] == 0.0
            @test overlap_matrix[2, 1] == 0.0
        end

        @testset "Realistic scenario: timestamp-based overlap with 11-month intersection" begin
            # Simulates white-tests scenario
            # 010415: 2 years of data (2022-09-01 to 2024-09-01)
            # 013614/013894: 1 year of data (2023-10-01 to 2024-10-01)
            # Intersection: 2023-10-01 to 2024-09-01 ≈ 11 months

            mast_ts = Dict(
                "010415" => create_mock_timeseries(DateTime(2022, 9, 1), DateTime(2024, 9, 1) - Minute(10), Minute(10), 120.0),
                "013614" => create_mock_timeseries(DateTime(2023, 10, 1), DateTime(2024, 10, 1) - Minute(10), Minute(10), 120.0),
                "013894" => create_mock_timeseries(DateTime(2023, 10, 1), DateTime(2024, 10, 1) - Minute(10), Minute(10), 120.0)
            )

            overlap_matrix = calculate_pairwise_overlap(mast_ts, 120)

            # 010415 ↔ 013614: intersection = 2023-10-01 to 2024-09-01 ≈ 11 months
            # With 10-min intervals: ~11*30*24*6 = ~47,520 timestamps
            # relative ≈ 335 days / 365 days ≈ 0.918
            # absolute ≈ 335 days / 120 days ≈ 2.79
            # max ≈ 2.79 > 0.8 threshold ✓
            @test overlap_matrix[1, 2] > 0.8  # Should exceed clustering threshold
            @test overlap_matrix[1, 3] > 0.8  # 010415 ↔ 013894

            # 013614 ↔ 013894: identical timestamps = full overlap
            @test overlap_matrix[2, 3] >= 1.0

            println("\n📊 Test: Timestamp-based overlap (11-month intersection)")
            println("  010415 ↔ 013614: overlap = $(round(overlap_matrix[1,2], digits=3))")
            println("  010415 ↔ 013894: overlap = $(round(overlap_matrix[1,3], digits=3))")
            println("  013614 ↔ 013894: overlap = $(round(overlap_matrix[2,3], digits=3))")
            println("  All should cluster together if threshold=0.8")
        end

        @testset "Three masts with varying overlaps" begin
            mast_ts = Dict(
                "M01" => create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 80.0),
                "M02" => create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 100.0),
                "M03" => create_mock_timeseries(DateTime(2023, 6, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 120.0)
            )

            overlap_matrix = calculate_pairwise_overlap(mast_ts, 120)

            @test size(overlap_matrix) == (3, 3)
            @test overlap_matrix[1, 2] >= 1.0  # Full overlap (all timestamps match)
            @test overlap_matrix[1, 3] >= 0.5  # Partial overlap (Jun-Dec)
            @test overlap_matrix[2, 3] >= 0.5  # Partial overlap
            # Check symmetry
            @test overlap_matrix[1, 2] == overlap_matrix[2, 1]
            @test overlap_matrix[1, 3] == overlap_matrix[3, 1]
            @test overlap_matrix[2, 3] == overlap_matrix[3, 2]
        end

        @testset "Timestamp-based: data gaps reduce overlap" begin
            # Create two 12-month masts with same time range but different data gaps
            # M01: complete data (no missing)
            # M02: 50% missing data in first 6 months, complete in last 6 months

            # M01: Full year of complete data
            ts1 = create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 80.0)

            # M02: Create with gaps by setting first half to missing
            ts2 = create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 100.0)
            mid_point = div(nrow(ts2.df), 2)
            ts2.df[1:mid_point, :ws] .= missing

            mast_ts = Dict("M01" => ts1, "M02" => ts2)
            overlap_matrix = calculate_pairwise_overlap(mast_ts, 120)

            # Overlap should be ~6 months (only second half where M02 has data)
            # relative = 182.5 / 365 ≈ 0.5
            # absolute = 182.5 / 120 ≈ 1.52
            # max ≈ 1.52
            @test overlap_matrix[1, 2] > 1.0  # absolute criterion wins
            @test overlap_matrix[1, 2] < 2.0  # but not full year

            println("\n📊 Test: Data gaps reduce overlap")
            println("  M01 (complete) ↔ M02 (50% missing): overlap = $(round(overlap_matrix[1,2], digits=3))")
            println("  Expected ~1.5 (6 months / 120 days threshold)")
        end
    end

    @testset "cluster_masts_by_overlap" begin
        @testset "Two masts above threshold form single cluster" begin
            mast_names = ["M01", "M02"]
            overlap_matrix = [1.0 0.9; 0.9 1.0]

            clusters = cluster_masts_by_overlap(mast_names, overlap_matrix, 0.8)

            @test length(clusters) == 1
            cluster_masts = first(values(clusters))
            @test length(cluster_masts) == 2
            @test "M01" ∈ cluster_masts
            @test "M02" ∈ cluster_masts
        end

        @testset "Two masts below threshold form separate clusters" begin
            mast_names = ["M01", "M02"]
            overlap_matrix = [1.0 0.5; 0.5 1.0]

            clusters = cluster_masts_by_overlap(mast_names, overlap_matrix, 0.8)

            @test length(clusters) == 2
        end

        @testset "Three masts: two cluster together, one isolated" begin
            mast_names = ["M01", "M02", "M03"]
            overlap_matrix = [
                1.0 0.9 0.3;
                0.9 1.0 0.3;
                0.3 0.3 1.0
            ]

            clusters = cluster_masts_by_overlap(mast_names, overlap_matrix, 0.8)

            @test length(clusters) == 2
            # Find the cluster with 2 masts
            two_mast_cluster = filter(c -> length(c) == 2, collect(values(clusters)))
            @test length(two_mast_cluster) == 1
            cluster_masts = first(two_mast_cluster)
            @test "M01" ∈ cluster_masts
            @test "M02" ∈ cluster_masts
        end

        @testset "Complete linkage: all pairs must exceed threshold" begin
            # A-B: 0.9, B-C: 0.9, A-C: 0.7
            # With complete linkage, A and C are too far apart (0.7 < 0.8)
            # So should not form single cluster
            mast_names = ["M01", "M02", "M03"]
            overlap_matrix = [
                1.0 0.9 0.7;
                0.9 1.0 0.9;
                0.7 0.9 1.0
            ]

            clusters = cluster_masts_by_overlap(mast_names, overlap_matrix, 0.8)

            # Complete linkage should split into 2 clusters: {M01, M02} or {M02, M03}, and one isolated
            # OR all 3 separate depending on implementation
            @test length(clusters) >= 2
        end

        @testset "Single mast returns single cluster" begin
            mast_names = ["M01"]
            overlap_matrix = [1.0;;]

            clusters = cluster_masts_by_overlap(mast_names, overlap_matrix, 0.8)

            @test length(clusters) == 1
            @test "M01" ∈ first(values(clusters))
        end

        @testset "Four masts all cluster together" begin
            mast_names = ["M01", "M02", "M03", "M04"]
            # All pairs have high overlap
            overlap_matrix = [
                1.0 0.95 0.9 0.85;
                0.95 1.0 0.92 0.88;
                0.9 0.92 1.0 0.9;
                0.85 0.88 0.9 1.0
            ]

            clusters = cluster_masts_by_overlap(mast_names, overlap_matrix, 0.8)

            @test length(clusters) == 1
            cluster_masts = first(values(clusters))
            @test length(cluster_masts) == 4
        end
    end

    @testset "determine_target_period_years" begin
        @testset "Floor with 0.8 threshold" begin
            @test determine_target_period_years(400) == 1    # 1.1 years: 0.1 < 0.8 → floor → 1
            @test determine_target_period_years(511) == 1    # 1.4 years: 0.4 < 0.8 → floor → 1
            @test determine_target_period_years(548) == 1    # 1.5 years: 0.5 < 0.8 → floor → 1
            @test determine_target_period_years(600) == 1    # 1.6 years: 0.6 < 0.8 → floor → 1
            @test determine_target_period_years(657) == 2    # 1.8 years: 0.8 = 0.8 → ceil → 2
            @test determine_target_period_years(658) == 2    # 1.803 years: 0.803 > 0.8 → ceil → 2
            @test determine_target_period_years(840) == 2    # 2.3 years: 0.3 < 0.8 → floor → 2
            @test determine_target_period_years(949) == 2    # 2.6 years: 0.6 < 0.8 → floor → 2
            @test determine_target_period_years(1303) == 3   # 3.57 years: 0.57 < 0.8 → floor → 3
        end

        @testset "Minimum 1 year" begin
            @test determine_target_period_years(100) == 1    # 0.3 years → 1 year minimum
            @test determine_target_period_years(200) == 1    # 0.5 years → 1 year
            @test determine_target_period_years(365) == 1    # 1.0 years → 1 year
        end

        @testset "Multi-year scenarios" begin
            @test determine_target_period_years(1277) == 3   # 3.5 years: 0.5 < 0.8 → floor → 3
            @test determine_target_period_years(1388) == 4   # 3.803 years: 0.803 > 0.8 → ceil → 4
            @test determine_target_period_years(1642) == 4   # 4.5 years: 0.5 < 0.8 → floor → 4
            @test determine_target_period_years(1753) == 5   # 4.803 years: 0.803 > 0.8 → ceil → 5
            @test determine_target_period_years(1825) == 5   # 5.0 years: 0.0 < 0.8 → floor → 5
            @test determine_target_period_years(2007) == 5   # 5.5 years: 0.5 < 0.8 → floor → 5
            @test determine_target_period_years(2118) == 6   # 5.803 years: 0.803 > 0.8 → ceil → 6
        end
    end

    @testset "calculate_union_time_range" begin
        @testset "Two masts with overlapping periods" begin
            mast_ts = Dict(
                "M01" => create_mock_timeseries(
                    DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 80.0
                ),
                "M02" => create_mock_timeseries(
                    DateTime(2023, 6, 1), DateTime(2024, 6, 30, 23, 50, 0), Minute(10), 100.0
                )
            )

            union_start, union_end = calculate_union_time_range(mast_ts)

            @test union_start == Date(2023, 1, 1)
            @test union_end == Date(2024, 6, 30)
        end

        @testset "Single mast" begin
            mast_ts = Dict(
                "M01" => create_mock_timeseries(
                    DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 80.0
                )
            )

            union_start, union_end = calculate_union_time_range(mast_ts)

            @test union_start == Date(2023, 1, 1)
            @test union_end == Date(2023, 12, 31)
        end
    end

    @testset "score_cluster_window" begin
        @testset "Full coverage window" begin
            mast_ts = Dict(
                "M01" => create_mock_timeseries(
                    DateTime(2023, 1, 1, 0, 0, 0), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 80.0
                )
            )

            window_start = Date(2023, 1, 1)
            window_end = Date(2023, 1, 31)

            score = score_cluster_window(mast_ts, window_start, window_end)

            @test score > 0.9  # Should have very high coverage
        end

        @testset "Average across multiple masts" begin
            mast_ts = Dict(
                "M01" => create_mock_timeseries(
                    DateTime(2023, 1, 1, 0, 0, 0), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 80.0
                ),
                "M02" => create_mock_timeseries(
                    DateTime(2023, 1, 1, 0, 0, 0), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 100.0
                )
            )

            window_start = Date(2023, 1, 1)
            window_end = Date(2023, 1, 31)

            score = score_cluster_window(mast_ts, window_start, window_end)

            @test score > 0.9  # Both have high coverage
        end
    end

    @testset "calculate_cluster_optimal_period" begin
        @testset "Single mast cluster with 1-year data" begin
            mast_ts = Dict(
                "M01" => create_mock_timeseries(
                    DateTime(2023, 1, 1, 0, 0, 0), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 80.0
                )
            )

            meso_ts = create_mock_timeseries(
                DateTime(2023, 1, 1, 0, 0, 0), DateTime(2024, 12, 31, 23, 0, 0), Hour(1), 100.0
            )

            time_range = calculate_cluster_optimal_period(["M01"], mast_ts, meso_ts)

            @test day(time_range.min) == 1  # Month-aligned
            @test time_range.max == time_range.min + Year(1) - Second(1)  # Exactly 1 year
        end

        @testset "Two masts with 2-year union" begin
            mast_ts = Dict(
                "M01" => create_mock_timeseries(
                    DateTime(2022, 1, 1, 0, 0, 0), DateTime(2022, 12, 31, 23, 50, 0), Minute(10), 80.0
                ),
                "M02" => create_mock_timeseries(
                    DateTime(2023, 1, 1, 0, 0, 0), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 100.0
                )
            )

            meso_ts = create_mock_timeseries(
                DateTime(2022, 1, 1, 0, 0, 0), DateTime(2024, 12, 31, 23, 0, 0), Hour(1), 100.0
            )

            time_range = calculate_cluster_optimal_period(["M01", "M02"], mast_ts, meso_ts)

            @test day(time_range.min) == 1  # Month-aligned
            @test time_range.max == time_range.min + Year(2) - Second(1)  # Exactly 2 years
        end

        @testset "Meso extends beyond mast union (6 months → 1 year)" begin
            mast_ts = Dict(
                "M01" => create_mock_timeseries(
                    DateTime(2023, 1, 1, 0, 0, 0), DateTime(2023, 6, 30, 23, 50, 0), Minute(10), 80.0
                )
            )

            meso_ts = create_mock_timeseries(
                DateTime(2020, 1, 1, 0, 0, 0), DateTime(2024, 12, 31, 23, 0, 0), Hour(1), 100.0
            )

            # 6 months mast union rounds to 1 year target
            # Meso extends beyond mast data to fill the 1-year period
            time_range = calculate_cluster_optimal_period(["M01"], mast_ts, meso_ts)

            @test day(time_range.min) == 1  # Month-aligned
            @test time_range.max == time_range.min + Year(1) - Second(1)  # Exactly 1 year
        end
    end

    @testset "Integration Tests" begin
        @testset "Full workflow: overlap → clustering → period calculation" begin
            # Create 3 masts: M01 and M02 overlap highly, M03 is separate
            mast_ts = Dict(
                "M01" => create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 80.0),
                "M02" => create_mock_timeseries(DateTime(2023, 1, 1), DateTime(2023, 12, 31, 23, 50, 0), Minute(10), 100.0),
                "M03" => create_mock_timeseries(DateTime(2024, 1, 1), DateTime(2024, 12, 31, 23, 50, 0), Minute(10), 120.0)
            )

            # Step 1: Calculate overlap
            overlap_matrix = calculate_pairwise_overlap(mast_ts, 120)

            @test overlap_matrix[1, 2] >= 1.0  # M01-M02: full overlap (can exceed 1.0)
            @test overlap_matrix[1, 3] == 0.0  # M01-M03: no overlap
            @test overlap_matrix[2, 3] == 0.0  # M02-M03: no overlap

            # Step 2: Cluster
            mast_names = sort(collect(keys(mast_ts)))
            clusters = cluster_masts_by_overlap(mast_names, overlap_matrix, 0.8)

            @test length(clusters) == 2  # Two clusters

            # Find the cluster with 2 masts (M01 and M02)
            two_mast_cluster = filter(c -> length(c) == 2, collect(values(clusters)))
            @test length(two_mast_cluster) == 1
            cluster_masts = first(two_mast_cluster)
            @test "M01" ∈ cluster_masts
            @test "M02" ∈ cluster_masts

            # Step 3: Calculate cluster period (would need timeseries data)
            # Tested separately above
        end

        @testset "Meso extension: 1.6yr mast → 1yr target (0.6 < 0.8)" begin
            # Mast data: 1.6 years (2022-01-01 to 2023-07-31)
            mast_ts = Dict(
                "M01" => create_mock_timeseries(
                    DateTime(2022, 1, 1, 0, 0, 0), DateTime(2023, 7, 31, 23, 50, 0), Minute(10), 80.0
                )
            )

            # Meso data: 10 years (2015-01-01 to 2024-12-31)
            meso_ts = create_mock_timeseries(
                DateTime(2015, 1, 1, 0, 0, 0), DateTime(2024, 12, 31, 23, 0, 0), Hour(1), 100.0
            )

            # 1.6 years: 0.6 < 0.8 → floor → 1 year target
            time_range = calculate_cluster_optimal_period(["M01"], mast_ts, meso_ts)

            # Should return a 1-year period
            @test day(time_range.min) == 1  # Month-aligned
            @test time_range.max == time_range.min + Year(1) - Second(1)  # Exactly 1 year

            # The period should favor the window containing most mast data
            # Mast data is 2022-01 to 2023-07
            @test year(time_range.min) >= 2022
            @test year(time_range.max) <= 2024
        end

        @testset "Meso extension: 3.57yr mast → 3yr target (real scenario)" begin
            # Simulate user's actual case: 1303 days ≈ 3.57 years
            # Create mast data spanning Jan 2020 to Aug 2023 (≈3.57 years)
            mast_ts = Dict(
                "M01" => create_mock_timeseries(
                    DateTime(2020, 1, 1, 0, 0, 0), DateTime(2023, 8, 15, 23, 50, 0), Minute(10), 80.0
                ),
                "M02" => create_mock_timeseries(
                    DateTime(2020, 3, 1, 0, 0, 0), DateTime(2023, 7, 31, 23, 50, 0), Minute(10), 90.0
                )
            )

            # Meso data: Long period (2015-01-01 to 2025-12-31)
            meso_ts = create_mock_timeseries(
                DateTime(2015, 1, 1, 0, 0, 0), DateTime(2025, 12, 31, 23, 0, 0), Hour(1), 100.0
            )

            # 3.57 years: 0.57 < 0.8 → floor → 3 years target
            time_range = calculate_cluster_optimal_period(["M01", "M02"], mast_ts, meso_ts)

            # Should return a 3-year period
            @test day(time_range.min) == 1  # Month-aligned
            @test time_range.max == time_range.min + Year(3) - Second(1)  # Exactly 3 years

            # The period should maximize overlap with mast data (2020-01 to 2023-08)
            @test year(time_range.min) >= 2019
            @test year(time_range.max) <= 2024
        end

        @testset "Meso extension: Period selection favors mast data" begin
            # Mast data: 1 year in the middle of meso range
            mast_ts = Dict(
                "M01" => create_mock_timeseries(
                    DateTime(2020, 6, 1, 0, 0, 0), DateTime(2021, 5, 31, 23, 50, 0), Minute(10), 80.0
                )
            )

            # Meso data: 10 years (2015-01-01 to 2024-12-31)
            meso_ts = create_mock_timeseries(
                DateTime(2015, 1, 1, 0, 0, 0), DateTime(2024, 12, 31, 23, 0, 0), Hour(1), 100.0
            )

            # 1 year mast → 1 year target
            time_range = calculate_cluster_optimal_period(["M01"], mast_ts, meso_ts)

            # Should select 1-year period that overlaps with mast data
            # Mast is 2020-06 to 2021-05, so selected period should be nearby
            @test day(time_range.min) == 1  # Month-aligned
            @test time_range.max == time_range.min + Year(1) - Second(1)

            # Period should be within or near mast data range
            @test year(time_range.min) >= 2020
            @test year(time_range.min) <= 2021
        end
    end
end
