using Test
using DataFrames
using Dates
using TOML
using CSV

# Import the modules we need to test
using CleanMastProject.Types.ParseSensorsConfig: InterpolationConfig, ParseSensorsFileConfig, from_dict, to_dict
using CleanMastProject.ParseSensors.CommandParseSensors: apply_interpolation
using CleanMastProject.Types.SensorColumns: ParsedSensor

@testset "InterpolationConfig Tests" begin
    @testset "InterpolationConfig creation and serialization" begin
        # Test creating InterpolationConfig
        config = InterpolationConfig(15, 10)
        @test config.from_minutes == 15
        @test config.to_minutes == 10
        
        # Test to_dict
        dict = to_dict(config)
        @test dict["from_minutes"] == 15
        @test dict["to_minutes"] == 10
        
        # Test from_dict
        config2 = from_dict(InterpolationConfig, dict)
        @test config2.from_minutes == 15
        @test config2.to_minutes == 10
    end
    
    @testset "ParseSensorsFileConfig with interpolation" begin
        # Test ParseSensorsFileConfig with interpolation
        interpolate_config = InterpolationConfig(15, 10)
        file_config = ParseSensorsFileConfig(
            "test.txt",
            "test",
            "sensor.toml",
            nothing,
            interpolate_config
        )
        
        @test file_config.interpolate == interpolate_config
        
        # Test serialization
        dict = to_dict(file_config)
        @test haskey(dict, "interpolate")
        @test dict["interpolate"]["from_minutes"] == 15
        @test dict["interpolate"]["to_minutes"] == 10
        
        # Test deserialization
        file_config2 = from_dict(ParseSensorsFileConfig, dict)
        @test !isnothing(file_config2.interpolate)
        @test file_config2.interpolate.from_minutes == 15
        @test file_config2.interpolate.to_minutes == 10
    end
    
    @testset "ParseSensorsFileConfig without interpolation" begin
        # Test ParseSensorsFileConfig without interpolation
        file_config = ParseSensorsFileConfig(
            "test.txt",
            "test",
            "sensor.toml",
            nothing,
            nothing
        )
        
        @test isnothing(file_config.interpolate)
        
        # Test serialization
        dict = to_dict(file_config)
        @test !haskey(dict, "interpolate")
        
        # Test deserialization
        file_config2 = from_dict(ParseSensorsFileConfig, dict)
        @test isnothing(file_config2.interpolate)
    end
    
    @testset "apply_interpolation function" begin
        # Create test data with 15-minute intervals
        timestamps = [
            DateTime(2024, 1, 1, 0, 0),
            DateTime(2024, 1, 1, 0, 15),
            DateTime(2024, 1, 1, 0, 30),
            DateTime(2024, 1, 1, 0, 45),
            DateTime(2024, 1, 1, 1, 0)
        ]
        
        df = DataFrame(
            timestamp = timestamps,
            ws_80m = [10.0, 12.0, 11.0, 13.0, 10.5],
            wd_80m = [180.0, 190.0, 185.0, 200.0, 175.0]
        )
        
        # Create test sensors
        sensors = [
            ParsedSensor(
                :ws_80m,
                "{sensorType}_{height}m_{statType}_{unit}",
                "WindSpeed",
                "N",
                80.0,
                "avg",
                "m/s"
            ),
            ParsedSensor(
                :wd_80m,
                "{sensorType}_{height}m_{statType}_{unit}",
                "WindDirection",
                "N",
                80.0,
                "avg",
                "deg"
            )
        ]
        
        # Create interpolation config (15 min -> 10 min)
        interpolate_config = InterpolationConfig(15, 10)
        
        # Apply interpolation
        result_df = apply_interpolation(df, sensors, interpolate_config)
        
        # Check that we have 10-minute intervals
        result_timestamps = sort(result_df.timestamp)
        intervals = diff(result_timestamps)
        @test all(intervals .== Minute(10))
        
        # Check that we have the expected number of points
        # From 0:00 to 1:00 with 10-minute intervals should give us 7 points (0, 10, 20, 30, 40, 50, 60)
        @test length(result_timestamps) == 7
        
        # Check that original timestamps are preserved where they align
        @test DateTime(2024, 1, 1, 0, 0) in result_timestamps
        @test DateTime(2024, 1, 1, 0, 30) in result_timestamps
        @test DateTime(2024, 1, 1, 1, 0) in result_timestamps
    end
end
