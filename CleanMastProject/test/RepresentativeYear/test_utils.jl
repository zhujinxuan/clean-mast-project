module TestRepresentativeYearUtils

using Test
using Dates
using DataFrames
using Statistics
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, TimeRange
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.RepresentativeYear.Utils

@testset "RepresentativeYear Utils" begin
    @testset "calculate_mean_speed" begin
        df = DataFrame(
            timestamp = [DateTime(2024,1,1,h) for h in 1:10],
            ws_100m = [8.0, 9.0, 7.0, 8.5, 9.5, 7.5, 8.0, 9.0, 7.0, 8.5]
        )
        sensor = SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s")
        ts = TimeSeriesData(df, [sensor])

        mean_speed = calculate_mean_speed(ts, sensor)
        @test mean_speed isa Float64
        @test mean_speed ≈ 8.2 atol=0.01

        df_with_missing = DataFrame(
            timestamp = [DateTime(2024,1,1,h) for h in 1:10],
            ws_100m = Vector{Union{Float64, Missing}}([missing, missing, missing, 8.5, 9.5, 7.5, 8.0, 9.0, 7.0, 8.5])
        )
        ts_with_missing = TimeSeriesData(df_with_missing, [sensor])
        mean_with_missing = calculate_mean_speed(ts_with_missing, sensor)
        @test !isnan(mean_with_missing)
        @test mean_with_missing ≈ 8.286 atol=0.01
    end

    @testset "find_climatology_timerange" begin
        range1 = find_climatology_timerange(DateTime(2024,1,1,0,0,0), DateTime(2025,12,31,23,0,0))
        @test range1.min == DateTime(2024,1,1,0,0,0)
        @test range1.max == DateTime(2025,12,31,23,59,59)

        @test_throws ErrorException find_climatology_timerange(DateTime(2024,3,15,12,0,0), DateTime(2025,10,20,8,0,0))

        range3 = find_climatology_timerange(DateTime(2023,12,31,23,0,0), DateTime(2025,1,1,1,0,0))
        @test range3.min == DateTime(2024,1,1,0,0,0)
        @test range3.max == DateTime(2024,12,31,23,59,59)

        range4 = find_climatology_timerange(DateTime(1990,1,1,0,0,0), DateTime(2025,12,31,23,0,0))
        @test range4.min == DateTime(1996,1,1,0,0,0)
        @test range4.max == DateTime(2025,12,31,23,59,59)
        @test year(range4.max) - year(range4.min) + 1 == 30

        @test_throws ErrorException find_climatology_timerange(DateTime(2024,6,1), DateTime(2024,8,1))
    end

    @testset "calculate_climatology_mean" begin
        timestamps = vcat(
            [DateTime(2023,6,1) + Hour(h) for h in 0:100],
            [DateTime(2024,1,1) + Hour(h) for h in 0:8759],
            [DateTime(2025,1,1) + Hour(h) for h in 0:8759],
            [DateTime(2026,1,1) + Hour(h) for h in 0:100]
        )

        ws_values = vcat(
            fill(6.0, 101),
            fill(8.0, 8760),
            fill(9.0, 8760),
            fill(12.0, 101)
        )

        df = DataFrame(timestamp = timestamps, ws_100m = ws_values)
        sensor = SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s")
        ts = TimeSeriesData(df, [sensor])

        climatology = calculate_climatology_mean(ts, sensor)
        @test climatology ≈ 8.5 atol=0.01

        complete_year_data = DataFrame(
            timestamp = [DateTime(2024,1,1) + Hour(h) for h in 0:8783],
            ws_100m = fill(7.5, 8784)
        )
        ts_complete = TimeSeriesData(complete_year_data, [sensor])
        @test calculate_climatology_mean(ts_complete, sensor) ≈ 7.5 atol=0.01

        partial_year_only = DataFrame(
            timestamp = [DateTime(2024,3,1) + Hour(h) for h in 0:100],
            ws_100m = fill(8.0, 101)
        )
        ts_partial = TimeSeriesData(partial_year_only, [sensor])
        @test_throws ErrorException calculate_climatology_mean(ts_partial, sensor)
    end

    @testset "is_calibration_needed" begin
        @test is_calibration_needed(10.0, 9.0)
        @test !is_calibration_needed(10.0, 9.9)
        @test is_calibration_needed(10.0, 11.0)
        @test is_calibration_needed(10.0, 9.0, threshold=0.05)
        @test !is_calibration_needed(10.0, 9.5, threshold=0.10)
    end

    @testset "find_representative_year" begin
        timestamps = vcat(
            [DateTime(2023,m,1) for m in 1:12],
            [DateTime(2024,m,1) for m in 1:12],
            [DateTime(2025,m,1) for m in 1:12]
        )

        ws_values = vcat(
            fill(7.0, 12),
            fill(8.0, 12),
            fill(7.9, 12)
        )

        df = DataFrame(
            timestamp = timestamps,
            ws_100m = ws_values
        )
        sensor = SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s")
        ts = TimeSeriesData(df, [sensor])

        ref_year = find_representative_year(ts, 8.0, sensor)
        @test ref_year isa DateTime
        @test year(ref_year) == 2025

        ref_year_strict = find_representative_year(ts, 7.95, sensor, threshold=0.01)
        @test year(ref_year_strict) == 2025
    end

    @testset "filter_training_range" begin
        df = DataFrame(
            timestamp = [DateTime(2024,1,1) + Day(i) for i in 0:365],
            ws_100m = fill(8.0, 366)
        )
        sensor = SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s")
        ts = TimeSeriesData(df, [sensor])

        range = TimeRange(DateTime(2024,3,1), DateTime(2024,6,30))
        filtered_ts = filter_training_range(ts, range)

        @test nrow(filtered_ts.df) < nrow(ts.df)
        @test all(range.min .<= filtered_ts.df.timestamp .<= range.max)
        @test filtered_ts.sensors == ts.sensors
    end

    @testset "find_target_mast_sensor" begin
        sensors = [
            SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s"),
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s"),
            SensorColumn(:ws_120m, "WindSpeed", "N", 120.0, "avg", "m/s")
        ]
        df = DataFrame(
            timestamp = [DateTime(2024,1,1)],
            ws_80m = [7.0],
            ws_100m = [8.0],
            ws_120m = [9.0]
        )
        ts = TimeSeriesData(df, sensors)

        @test find_target_mast_sensor(ts, 120.0).height == 120.0
        @test find_target_mast_sensor(ts, 110.0).height == 100.0
        @test find_target_mast_sensor(ts, 80.0).height == 80.0

        temp_only_ts = TimeSeriesData(
            DataFrame(timestamp = [DateTime(2024,1,1)], temp = [20.0]),
            [SensorColumn(:temp, "Temperature", "N", 80.0, "avg", "C")]
        )
        @test isnothing(find_target_mast_sensor(temp_only_ts, 80.0))
    end

    @testset "find_target_meso_sensor" begin
        sensors = [
            SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s"),
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s"),
            SensorColumn(:ws_120m, "WindSpeed", "N", 120.0, "avg", "m/s")
        ]
        df = DataFrame(
            timestamp = [DateTime(2024,1,1)],
            ws_80m = [7.0],
            ws_100m = [8.0],
            ws_120m = [9.0]
        )
        ts = TimeSeriesData(df, sensors)

        @test find_target_meso_sensor(ts, 120.0).height == 120.0
        @test find_target_meso_sensor(ts, 90.0).height == 80.0

        temp_only_ts = TimeSeriesData(
            DataFrame(timestamp = [DateTime(2024,1,1)], temp = [20.0]),
            [SensorColumn(:temp, "Temperature", "N", 80.0, "avg", "C")]
        )
        @test isnothing(find_target_meso_sensor(temp_only_ts, 80.0))
    end

    @testset "find_heighest_meso_sensor" begin
        sensors = [
            SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s"),
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s"),
            SensorColumn(:ws_120m, "WindSpeed", "N", 120.0, "avg", "m/s")
        ]
        df = DataFrame(
            timestamp = [DateTime(2024,1,1)],
            ws_80m = [7.0],
            ws_100m = [8.0],
            ws_120m = [9.0]
        )
        ts = TimeSeriesData(df, sensors)

        highest = find_heighest_meso_sensor(ts)
        @test !isnothing(highest)
        @test highest.height == 120.0

        single_sensor_ts = TimeSeriesData(
            DataFrame(timestamp = [DateTime(2024,1,1)], ws_100m = [8.0]),
            [SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s")]
        )
        @test find_heighest_meso_sensor(single_sensor_ts).height == 100.0

        no_ws_ts = TimeSeriesData(
            DataFrame(timestamp = [DateTime(2024,1,1)], temp = [20.0]),
            [SensorColumn(:temp, "Temperature", "N", 80.0, "avg", "C")]
        )
        @test isnothing(find_heighest_meso_sensor(no_ws_ts))
    end
end

end
