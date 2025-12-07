module TestGuessMastFromMeso

using Test
using Dates
using DataFrames
using Statistics
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, TimeRange, SensorColumn
using CleanMastProject.Types.GuessMastFromMesoConfig: GuessMastTarget
using CleanMastProject.GuessMastFromMeso.Core: find_highest_direction_sensor,
                                                find_direction_sensors_by_height,
                                                calculate_direction_veer,
                                                interpolate_wind_direction,
                                                create_scaled_sensor

@testset "GuessMastFromMeso Core Functions" begin
    @testset "find_highest_direction_sensor" begin
        sensors = [
            SensorColumn(:wd_80m, "WindDirection", "N", 80.0, "avg", "deg"),
            SensorColumn(:wd_100m, "WindDirection", "N", 100.0, "avg", "deg"),
            SensorColumn(:wd_120m, "WindDirection", "N", 120.0, "avg", "deg")
        ]
        df = DataFrame(
            timestamp = [DateTime(2024,1,1)],
            wd_80m = [45.0],
            wd_100m = [50.0],
            wd_120m = [55.0]
        )
        ts = TimeSeriesData(df, sensors)

        highest = find_highest_direction_sensor(ts)
        @test !isnothing(highest)
        @test highest.height == 120.0
        @test highest.sensorType == "WindDirection"

        single_sensor_ts = TimeSeriesData(
            DataFrame(timestamp = [DateTime(2024,1,1)], wd_100m = [50.0]),
            [SensorColumn(:wd_100m, "WindDirection", "N", 100.0, "avg", "deg")]
        )
        @test find_highest_direction_sensor(single_sensor_ts).height == 100.0

        no_wd_ts = TimeSeriesData(
            DataFrame(timestamp = [DateTime(2024,1,1)], ws_100m = [8.0]),
            [SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s")]
        )
        @test isnothing(find_highest_direction_sensor(no_wd_ts))
    end

    @testset "find_direction_sensors_by_height" begin
        sensors = [
            SensorColumn(:wd_120m, "WindDirection", "N", 120.0, "avg", "deg"),
            SensorColumn(:wd_80m, "WindDirection", "N", 80.0, "avg", "deg"),
            SensorColumn(:wd_100m, "WindDirection", "N", 100.0, "avg", "deg")
        ]
        df = DataFrame(timestamp = [DateTime(2024,1,1)])
        ts = TimeSeriesData(df, sensors)

        sorted_sensors = find_direction_sensors_by_height(ts)
        @test length(sorted_sensors) == 3
        @test sorted_sensors[1].height == 80.0
        @test sorted_sensors[2].height == 100.0
        @test sorted_sensors[3].height == 120.0
    end

    @testset "calculate_direction_veer" begin
        df = DataFrame(
            timestamp = [DateTime(2024,1,1,h) for h in 1:10],
            wd_80m = [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0, 350.0, 10.0],
            wd_100m = [5.0, 50.0, 95.0, 140.0, 185.0, 230.0, 275.0, 320.0, 355.0, 15.0]
        )
        wd_low = SensorColumn(:wd_80m, "WindDirection", "N", 80.0, "avg", "deg")
        wd_high = SensorColumn(:wd_100m, "WindDirection", "N", 100.0, "avg", "deg")

        veer = calculate_direction_veer(df, wd_low, wd_high)
        @test veer ≈ 5.0 atol=0.1

        df_with_missing = DataFrame(
            timestamp = [DateTime(2024,1,1,h) for h in 1:5],
            wd_80m = [0.0, missing, 90.0, 135.0, missing],
            wd_100m = [5.0, 50.0, 95.0, missing, 185.0]
        )
        veer_sparse = calculate_direction_veer(df_with_missing, wd_low, wd_high)
        @test veer_sparse ≈ 5.0 atol=0.1
    end

    @testset "interpolate_wind_direction" begin
        base_sensor = SensorColumn(:wd_100m, "WindDirection", "N", 100.0, "avg", "deg")
        df = DataFrame(
            timestamp = [DateTime(2024,1,1,h) for h in 1:5],
            wd_100m = [0.0, 90.0, 180.0, 270.0, 350.0]
        )

        veer_per_meter = 0.5
        target_height = 120.0

        new_sensor, interpolated_values = interpolate_wind_direction(base_sensor, target_height, veer_per_meter, df)

        @test new_sensor.columnName == :WindDirection_120m_avg
        @test new_sensor.height == 120.0
        @test new_sensor.sensorType == "WindDirection"

        @test interpolated_values[1] ≈ 10.0 atol=0.01
        @test interpolated_values[2] ≈ 100.0 atol=0.01
        @test interpolated_values[3] ≈ 190.0 atol=0.01
        @test interpolated_values[4] ≈ 280.0 atol=0.01
        @test interpolated_values[5] ≈ 0.0 atol=0.01
    end

    @testset "create_scaled_sensor" begin
        base_sensor = SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s")
        df = DataFrame(
            timestamp = [DateTime(2024,1,1,h) for h in 1:5],
            ws_100m = [8.0, 9.0, missing, 7.0, 8.5]
        )

        target_height = 120.0
        scale_factor = 1.1

        new_sensor, scaled_values = create_scaled_sensor(base_sensor, target_height, scale_factor, df)

        @test new_sensor.columnName == :WindSpeed_120m_avg
        @test new_sensor.height == 120.0
        @test new_sensor.sensorType == "WindSpeed"
        @test new_sensor.statType == "avg"

        @test length(scaled_values) == 5
        @test scaled_values[1] ≈ 8.8 atol=0.01
        @test scaled_values[2] ≈ 9.9 atol=0.01
        @test ismissing(scaled_values[3])
        @test scaled_values[4] ≈ 7.7 atol=0.01
        @test scaled_values[5] ≈ 9.35 atol=0.01
    end

    @testset "interpolate_wind_direction with zero veer (copy behavior)" begin
        base_sensor = SensorColumn(:wd_100m, "WindDirection", "N", 100.0, "avg", "deg")
        df = DataFrame(
            timestamp = [DateTime(2024,1,1,h) for h in 1:5],
            wd_100m = [45.0, 90.0, missing, 135.0, 270.0]
        )

        target_height = 120.0
        veer_per_meter = 0.0
        new_sensor, wd_values = interpolate_wind_direction(base_sensor, target_height, veer_per_meter, df)

        @test new_sensor.columnName == :WindDirection_120m_avg
        @test new_sensor.height == 120.0
        @test new_sensor.sensorType == "WindDirection"
        @test new_sensor.statType == "avg"

        @test length(wd_values) == 5
        @test wd_values[1] ≈ 45.0 atol=0.01
        @test wd_values[2] ≈ 90.0 atol=0.01
        @test ismissing(wd_values[3])
        @test wd_values[4] ≈ 135.0 atol=0.01
        @test wd_values[5] ≈ 270.0 atol=0.01
    end

    @testset "GuessMastTarget type" begin
        target = GuessMastTarget(100.0, 7.5)

        @test target.height == 100.0
        @test target.mean_speed == 7.5
    end
end

end
