using Test
using DataFrames
using Dates
using CleanMastProject.ReconstructSingleMast.DirectionTraining
using CleanMastProject.MastTimeSeries
using CleanMastProject.Types.ReconstructSingleMast

function create_test_data()::TimeSeriesData
    df = DataFrame(
        timestamp = DateTime(2024,1,1):Hour(1):DateTime(2024,1,2),
        wd_60m = [350.0, 10.0, missing, 355.0, 5.0],
        wd_40m = [355.0, 5.0, 0.0, missing, 10.0],
        ws_60m = [5.0, 6.0, missing, 5.5, 6.5],
        ws_40m = [4.5, 5.5, 4.0, missing, 6.0]
    )

    sensors = [
        SensorColumn(:wd_60m, "WindDirection", "N", 60.0, "avg", "deg"),
        SensorColumn(:wd_40m, "WindDirection", "N", 40.0, "avg", "deg"),
        SensorColumn(:ws_60m, "WindSpeed", "N", 60.0, "avg", "m/s"),
        SensorColumn(:ws_40m, "WindSpeed", "N", 40.0, "avg", "m/s")
    ]

    TimeSeriesData(df, sensors)
end

@testset "DirectionTraining" begin
    @testset "direction_to_vector and vector_to_direction" begin
        direction = 45.0
        x, y = direction_to_vector(direction)
        
        @test x ≈ sqrt(2)/2 atol=1e-6
        @test y ≈ sqrt(2)/2 atol=1e-6
        
        reconstructed = vector_to_direction(x, y)
        @test reconstructed ≈ direction atol=1e-6
    end

    @testset "calculate_vector_average" begin
        data = create_test_data()
        direction_sensor = first(filter(s -> s.sensorType == "WindDirection", data.sensors))
        speed_sensor = first(filter(s -> s.sensorType == "WindSpeed", data.sensors))
        
        result = calculate_vector_average(data, direction_sensor, speed_sensor)
        @test !isnothing(result)
        @test length(result) == 3  # x, y, weight
    end

    @testset "reconstruct_wind_directions integration" begin
        data = create_test_data()
        successes, failures = reconstruct_wind_directions(data)
        
        @test !isempty(successes)
        @test all(s -> s isa ReconstructedSuccess, successes)
        @test all(f -> f isa ReconstructedFailure, failures)
        
        # Check that we got reconstructions for missing values
        missing_timestamps = [DateTime(2024,1,1) + Hour(2), 
                            DateTime(2024,1,1) + Hour(3)]
        @test all(s -> s.timestamp in missing_timestamps, successes)
    end
end 