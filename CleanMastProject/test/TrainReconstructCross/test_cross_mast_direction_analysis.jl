"""
    test_cross_mast_direction_analysis.jl

Comprehensive test suite for CrossMastDirectionAnalysis.jl module in cross-mast reconstruction system.
Tests direction difference analysis, circular mathematics, and direction model training/reconstruction.
"""

using Test
using DataFrames
using Dates
using Statistics
using Random

# Import the modules we need to test
using CleanMastProject.TrainReconstructCross.CrossMastDirectionAnalysis
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.Types.CrossMastDirectionModels: CrossMastDirectionModel, CrossMastDirectionPair
using CleanMastProject.Types.CrossMastTrainParams: CrossMastDirectionTrainParams

@testset "CrossMastDirectionAnalysis.jl Tests" begin

    @testset "Circular Mathematics Tests" begin
        
        @testset "test_normalize_direction" begin
            # Basic normalization
            @test normalize_direction(180.0) ≈ 180.0
            @test normalize_direction(0.0) ≈ 0.0
            @test normalize_direction(359.0) ≈ 359.0
            
            # Values above 360
            @test normalize_direction(361.0) ≈ 1.0
            @test normalize_direction(450.0) ≈ 90.0
            @test normalize_direction(720.0) ≈ 0.0
            
            # Negative values
            @test normalize_direction(-1.0) ≈ 359.0
            @test normalize_direction(-90.0) ≈ 270.0
            @test normalize_direction(-361.0) ≈ 359.0
            
            # Large values
            @test normalize_direction(1080.0) ≈ 0.0  # 3 full rotations
            @test normalize_direction(-720.0) ≈ 0.0  # -2 full rotations
        end

        @testset "test_circular_difference" begin
            # Small realistic differences (typical for wind direction correction)
            @test circular_difference(10.0, 5.0) ≈ 5.0
            @test circular_difference(5.0, 10.0) ≈ -5.0
            @test circular_difference(200.0, 180.0) ≈ 20.0
            @test circular_difference(180.0, 200.0) ≈ -20.0
            
            # Boundary crossing tests (most important for wind direction analysis)
            @test circular_difference(10.0, 350.0) ≈ 20.0  # Not 340.0!
            @test circular_difference(350.0, 10.0) ≈ -20.0  # Not -340.0!
            @test circular_difference(1.0, 359.0) ≈ 2.0
            @test circular_difference(359.0, 1.0) ≈ -2.0
            @test circular_difference(15.0, 345.0) ≈ 30.0  # Common wind direction offset
            @test circular_difference(345.0, 15.0) ≈ -30.0
            
            # Medium differences (still within reconstruction range)
            @test circular_difference(90.0, 60.0) ≈ 30.0
            @test circular_difference(60.0, 90.0) ≈ -30.0
            @test circular_difference(270.0, 240.0) ≈ 30.0
            @test circular_difference(240.0, 270.0) ≈ -30.0
            
            # Same values (perfect alignment)
            @test circular_difference(0.0, 0.0) ≈ 0.0
            @test circular_difference(180.0, 180.0) ≈ 0.0
            @test circular_difference(359.0, 359.0) ≈ 0.0
            
            # Quarter rotations (mainly for mathematical completeness)
            @test circular_difference(90.0, 0.0) ≈ 90.0
            @test circular_difference(180.0, 90.0) ≈ 90.0
            @test circular_difference(270.0, 180.0) ≈ 90.0
            @test circular_difference(0.0, 270.0) ≈ 90.0
        end
    end

    @testset "Core Functionality Tests" begin
        
        @testset "test_analyze_winddirection_differences" begin
            # Create two masts with multiple direction sensors
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:143]  # 1 day
            
            Random.seed!(456)
            base_directions = rand(144) * 360  # Random base directions
            
            # Target mast: 120m and 160m sensors
            target_120_dirs = base_directions .+ randn(144) * 3.0
            target_160_dirs = base_directions .+ 5.0 .+ randn(144) * 2.0  # 5° offset + less noise
            
            # Source mast: 100m and 140m sensors  
            source_100_dirs = base_directions .+ 10.0 .+ randn(144) * 4.0  # 10° offset + more noise
            source_140_dirs = base_directions .+ 8.0 .+ randn(144) * 3.0   # 8° offset + medium noise
            
            target_df = DataFrame(
                timestamp=timestamps, 
                WD_120m=target_120_dirs,
                WD_160m=target_160_dirs
            )
            source_df = DataFrame(
                timestamp=timestamps,
                WD_100m=source_100_dirs, 
                WD_140m=source_140_dirs
            )
            
            target_sensors = [
                SensorColumn(sensorType="WindDirection", statType="avg", height=120.0, columnName=:WD_120m, sensorDirection="N", unit="deg"),
                SensorColumn(sensorType="WindDirection", statType="avg", height=160.0, columnName=:WD_160m, sensorDirection="N", unit="deg")
            ]
            source_sensors = [
                SensorColumn(sensorType="WindDirection", statType="avg", height=100.0, columnName=:WD_100m, sensorDirection="N", unit="deg"),
                SensorColumn(sensorType="WindDirection", statType="avg", height=140.0, columnName=:WD_140m, sensorDirection="N", unit="deg")
            ]
            
            target_ts = TimeSeriesData(target_df, target_sensors)
            source_ts = TimeSeriesData(source_df, source_sensors)
            
            results = analyze_winddirection_differences(target_ts, source_ts)
            
            # Should have 4 pairs (2 target × 2 source)
            @test length(results) == 4
            
            # All results should have sufficient data points
            @test all(r -> r.data_points >= 100, results)
            
            # Check that sensors are properly paired
            sensor_pairs = [(r.target_sensor.height, r.source_sensor.height) for r in results]
            expected_pairs = [(120.0, 100.0), (120.0, 140.0), (160.0, 100.0), (160.0, 140.0)]
            @test Set(sensor_pairs) == Set(expected_pairs)
            
            # Offsets should be in reasonable ranges based on our test data
            @test all(r -> abs(r.offset) < 30.0, results)  # Should detect reasonable offsets
            @test all(r -> r.std_deviation > 0.0, results)  # Should have some variation
            @test all(r -> r.std_deviation < 20.0, results)  # But not excessive variation
        end
    end

    @testset "Edge Case Tests" begin
        
        @testset "test_no_direction_sensors" begin
            # No wind direction sensors in target
            timestamps = [DateTime(2023,1,1)]
            target_df = DataFrame(timestamp=timestamps, WS_120m=[12.0])
            source_df = DataFrame(timestamp=timestamps, WD_100m=[180.0])
            
            target_sensors = [SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")]
            source_sensors = [SensorColumn(sensorType="WindDirection", statType="avg", height=100.0, columnName=:WD_100m, sensorDirection="N", unit="deg")]
            
            target_ts = TimeSeriesData(target_df, target_sensors)
            source_ts = TimeSeriesData(source_df, source_sensors)
            
            results = analyze_winddirection_differences(target_ts, source_ts)
            @test isempty(results)
        end
    end

    @testset "Model Training Tests" begin
        
        @testset "test_train_direction_model_basic" begin
            # Create test data with good direction relationships
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:199]
            
            Random.seed!(789)
            base_directions = rand(200) * 360
            
            # Create pairs with different quality relationships
            target_120_dirs = base_directions .+ randn(200) * 2.0  # Low noise
            source_140_dirs = base_directions .+ 8.0 .+ randn(200) * 3.0   # Medium noise, 8° offset
            
            target_df = DataFrame(
                timestamp=timestamps,
                WD_120m=target_120_dirs
            )
            source_df = DataFrame(
                timestamp=timestamps, 
                WD_140m=source_140_dirs
            )
            
            target_sensors = [
                SensorColumn(sensorType="WindDirection", statType="avg", height=120.0, columnName=:WD_120m, sensorDirection="N", unit="deg")
            ]
            source_sensors = [
                SensorColumn(sensorType="WindDirection", statType="avg", height=140.0, columnName=:WD_140m, sensorDirection="N", unit="deg")
            ]
            
            target_ts = TimeSeriesData(target_df, target_sensors)
            source_ts = TimeSeriesData(source_df, source_sensors)
            
            # Train with permissive parameters
            params = CrossMastDirectionTrainParams(
                target_name="Target",
                source_name="Source",
                min_data_points=100,
                max_std_deviation=15.0,  # Allow all our test pairs
                max_abs_offset=20.0
            )
            
            model = train(CrossMastDirectionModel, params, target_ts, source_ts)
            
            @test model.target_mast_name == "Target"
            @test model.source_mast_name == "Source"
            @test length(model.pairs) == 1  # Should have 1 pair
            
            # Best pair should have reasonable std deviation
            @test model.pairs[1].std_deviation < 10.0
        end
    end

    @testset "Model Reconstruction Tests" begin
        
        @testset "test_reconstruct_direction_basic" begin
            # Create a simple model with known relationship
            target_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=120.0, columnName=:WD_120m, sensorDirection="N", unit="deg")
            source_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=100.0, columnName=:WD_100m, sensorDirection="N", unit="deg")
            
            # Model with 10° offset
            pair = CrossMastDirectionPair(
                target_sensor=target_sensor,
                source_sensor=source_sensor, 
                offset=10.0,
                std_deviation=2.0,
                data_points=200
            )
            
            model = CrossMastDirectionModel(
                target_mast_name="Target",
                source_mast_name="Source",
                pairs=[pair]
            )
            
            # Create source data to reconstruct from
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:9]
            source_directions = [0.0, 90.0, 180.0, 270.0, 350.0, 10.0, 120.0, 200.0, 300.0, 45.0]
            
            source_df = DataFrame(timestamp=timestamps, WD_100m=source_directions)
            source_ts = TimeSeriesData(source_df, [source_sensor])
            
            reconstructed_ts = reconstruct(model, source_ts)
            
            @test length(reconstructed_ts.sensors) == 1
            @test reconstructed_ts.sensors[1] == target_sensor
            @test nrow(reconstructed_ts.df) == 10
            
            # Check reconstructed values: should be source + 10° (with normalization)
            expected_directions = (source_directions .+ 10.0) .% 360
            actual_directions = reconstructed_ts.df.WD_120m
            
            for (expected, actual) in zip(expected_directions, actual_directions)
                @test actual ≈ expected atol=0.001
            end
        end
    end
end

# Helper Functions for Testing
"""
    create_direction_test_data(start_time, num_intervals, base_directions, offset, noise_std)

Create test direction data with specified offset and noise characteristics.
"""
function create_direction_test_data(start_time::DateTime, num_intervals::Int, 
                                  base_directions::Vector{Float64}, offset::Float64, noise_std::Float64)
    timestamps = [start_time + Minute(10*i) for i in 0:num_intervals-1]
    Random.seed!(42)  # For reproducible tests
    directions = (base_directions .+ offset .+ randn(num_intervals) * noise_std) .% 360
    return timestamps, directions
end

"""
    validate_circular_arithmetic(target_val, source_val, expected_offset, tolerance=2.0)

Validate that circular arithmetic was applied correctly.
"""
function validate_circular_arithmetic(target_val::Float64, source_val::Float64, expected_offset::Float64, tolerance::Float64=2.0)
    actual_offset = circular_difference(target_val, source_val)
    @test abs(actual_offset - expected_offset) <= tolerance
end

@testset "Helper Function Tests" begin
    @testset "test_helper_functions" begin
        # Test create_direction_test_data
        base_dirs = [0.0, 90.0, 180.0, 270.0]
        timestamps, directions = create_direction_test_data(DateTime(2023,1,1), 4, base_dirs, 10.0, 1.0)
        
        @test length(timestamps) == 4
        @test length(directions) == 4
        @test all(d -> 0.0 <= d < 360.0, directions)  # Should be normalized
        
        # Test validate_circular_arithmetic
        validate_circular_arithmetic(20.0, 10.0, 10.0)  # 20 - 10 = 10
        validate_circular_arithmetic(10.0, 350.0, 20.0)  # Boundary crossing
        validate_circular_arithmetic(350.0, 10.0, -20.0)  # Reverse boundary crossing
    end
end 