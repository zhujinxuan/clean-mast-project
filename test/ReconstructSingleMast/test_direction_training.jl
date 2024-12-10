using Test
using DataFrames
using Dates
using CleanMastProject.ReconstructSingleMast.DirectionTraining
using CleanMastProject.MastTimeSeries
using CleanMastProject.Types.ReconstructSingleMast

function create_test_data_for_vector_average()::TimeSeriesData
    timestamps = DateTime(2024,1,1):Minute(10):DateTime(2024,1,2)
    directions = [45.0 for _ in 1:length(timestamps)]
    speeds = Vector{Union{Missing, Float64}}([rand(3.0:0.1:5.0) for _ in 1:length(timestamps)])
    
    # Introduce missing values
    for i in 1:round(Int, 0.2 * length(speeds))
        idx = rand(1:length(speeds))
        speeds[idx] = missing
        directions[idx] = 270.0
    end

    df = DataFrame(
        timestamp = timestamps,
        direction = directions,
        speed = speeds
    )

    sensors = [
        SensorColumn(:direction, "WindDirection", "N", 98.0, "avg", "deg"),
        SensorColumn(:speed, "WindSpeed", "N", 100.0, "avg", "m/s")
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

    @testset "Vector Average Test" begin
        data = create_test_data_for_vector_average()
        direction_sensor = first(filter(s -> s.sensorType == "WindDirection", data.sensors))
        speed_sensor = first(filter(s -> s.sensorType == "WindSpeed", data.sensors))
        
        result = calculate_vector_average(data, direction_sensor, speed_sensor)
        @test !isnothing(result)
        
        # Extract the direction from the result
        average_direction, speed = result
        
        # Test if the average direction is approximately 45 degrees
        @test average_direction ≈ 45.0 atol=1e-6
        @test speed ≈ 4.0 atol=2
    end

end 