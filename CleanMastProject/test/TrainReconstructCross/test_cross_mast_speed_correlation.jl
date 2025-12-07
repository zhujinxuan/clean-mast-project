"""
    test_cross_mast_speed_correlation.jl

Comprehensive test suite for CrossMastSpeedCorrelation.jl module in cross-mast reconstruction system.
Tests wind speed correlation analysis, linear regression fitting, and speed model training/reconstruction.
"""

using Test
using DataFrames
using Dates
using Statistics
using Random

# Import the modules we need to test
using CleanMastProject.TrainReconstructCross.CrossMastSpeedCorrelation
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.Types.CrossMastSpeedModels: CrossMastSpeedModel, CrossMastSpeedPair
using CleanMastProject.Types.CrossMastTrainParams: CrossMastSpeedTrainParams

@testset "CrossMastSpeedCorrelation.jl Tests" begin

    @testset "Core Functionality Tests" begin
        
        @testset "test_analyze_windspeed_correlations" begin
            # Create two masts with multiple speed sensors
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:199]  # ~1.4 days
            
            Random.seed!(123)
            base_speeds = 8.0 .+ 4.0 * rand(200)  # Base speeds 8-12 m/s
            
            # Target mast: 120m and 160m sensors with realistic relationships
            target_120_speeds = base_speeds .+ randn(200) * 0.5  # Low noise
            target_160_speeds = base_speeds .* 1.08 .+ 0.3 .+ randn(200) * 0.3  # 8% higher + offset
            
            # Source mast: 100m and 140m sensors
            source_100_speeds = base_speeds .* 0.92 .- 0.2 .+ randn(200) * 0.6  # 8% lower - offset + more noise
            source_140_speeds = base_speeds .* 1.02 .+ 0.1 .+ randn(200) * 0.4  # 2% higher + small offset
            
            target_df = DataFrame(
                timestamp=timestamps,
                WS_120m=target_120_speeds,
                WS_160m=target_160_speeds
            )
            source_df = DataFrame(
                timestamp=timestamps,
                WS_100m=source_100_speeds,
                WS_140m=source_140_speeds
            )
            
            target_sensors = [
                SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s"),
                SensorColumn(sensorType="WindSpeed", statType="avg", height=160.0, columnName=:WS_160m, sensorDirection="N", unit="m/s")
            ]
            source_sensors = [
                SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s"),
                SensorColumn(sensorType="WindSpeed", statType="avg", height=140.0, columnName=:WS_140m, sensorDirection="N", unit="m/s")
            ]
            
            target_ts = TimeSeriesData(target_df, target_sensors)
            source_ts = TimeSeriesData(source_df, source_sensors)
            
            results = analyze_windspeed_correlations(target_ts, source_ts)
            
            # Should have 4 pairs (2 target × 2 source)
            @test length(results) == 4
            
            # All results should have sufficient data points
            @test all(r -> r.data_points >= 100, results)
            
            # Check that sensors are properly paired
            sensor_pairs = [(r.target_sensor.height, r.source_sensor.height) for r in results]
            expected_pairs = [(120.0, 100.0), (120.0, 140.0), (160.0, 100.0), (160.0, 140.0)]
            @test Set(sensor_pairs) == Set(expected_pairs)
            
            # All correlations should be positive and reasonable for wind speed relationships
            @test all(r -> r.correlation > 0.5, results)  # Should have good correlations
            @test all(r -> r.correlation <= 1.0, results)  # Cannot exceed 1.0
            
            # Slope should be positive for wind speed relationships
            @test all(r -> r.slope > 0.0, results)
            @test all(r -> 0.5 < r.slope < 2.0, results)  # Reasonable range for wind speed ratios
        end

        @testset "test_perfect_correlation" begin
            # Create perfectly correlated data
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:149]
            
            Random.seed!(456)
            base_speeds = 5.0 .+ 8.0 * rand(150)  # 5-13 m/s range
            
            # Perfect linear relationship: target = 1.2 * source + 0.5
            source_speeds = base_speeds
            target_speeds = source_speeds .* 1.2 .+ 0.5
            
            target_df = DataFrame(timestamp=timestamps, WS_120m=target_speeds)
            source_df = DataFrame(timestamp=timestamps, WS_100m=source_speeds)
            
            target_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")
            source_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")
            
            target_ts = TimeSeriesData(target_df, [target_sensor])
            source_ts = TimeSeriesData(source_df, [source_sensor])
            
            results = analyze_windspeed_correlations(target_ts, source_ts)
            
            @test length(results) == 1
            
            result = results[1]
            @test result.correlation ≈ 1.0 atol=0.001  # Perfect correlation
            @test result.slope ≈ 1.2 atol=0.01        # Correct slope
            @test result.intercept ≈ 0.5 atol=0.01     # Correct intercept
            @test result.data_points == 150
        end

        @testset "test_noisy_correlation" begin
            # Create data with realistic wind speed relationship but noise
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:199]
            
            Random.seed!(789)
            base_speeds = 6.0 .+ 6.0 * rand(200)  # 6-12 m/s
            
            # Relationship with noise: target = 0.9 * source + 1.0 + noise
            source_speeds = base_speeds
            target_speeds = source_speeds .* 0.9 .+ 1.0 .+ randn(200) * 1.0  # ±1 m/s noise
            
            target_df = DataFrame(timestamp=timestamps, WS_120m=target_speeds)
            source_df = DataFrame(timestamp=timestamps, WS_100m=source_speeds)
            
            target_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")
            source_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")
            
            target_ts = TimeSeriesData(target_df, [target_sensor])
            source_ts = TimeSeriesData(source_df, [source_sensor])
            
            results = analyze_windspeed_correlations(target_ts, source_ts)
            
            @test length(results) == 1
            
            result = results[1]
            @test result.correlation > 0.7   # Should still have good correlation despite noise
            @test result.correlation < 1.0   # But not perfect due to noise
            @test result.slope ≈ 0.9 atol=0.2  # Should detect approximate slope
            @test result.intercept ≈ 1.0 atol=0.5  # Should detect approximate intercept
        end
    end

    @testset "Edge Case Tests" begin
        
        @testset "test_insufficient_data" begin
            # Less than 100 data points
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:49]  # Only 50 points
            target_speeds = fill(10.0, 50)
            source_speeds = fill(9.0, 50)
            
            target_df = DataFrame(timestamp=timestamps, WS_120m=target_speeds)
            source_df = DataFrame(timestamp=timestamps, WS_100m=source_speeds)
            
            target_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")
            source_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")
            
            target_ts = TimeSeriesData(target_df, [target_sensor])
            source_ts = TimeSeriesData(source_df, [source_sensor])
            
            results = analyze_windspeed_correlations(target_ts, source_ts)
            
            @test isempty(results)  # Should return empty for insufficient data
        end

        @testset "test_missing_data" begin
            # 200 timestamps but many missing values
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:199]
            target_speeds = [i % 3 == 0 ? missing : 10.0 for i in 1:200]  # ~67% missing
            source_speeds = [i % 4 == 0 ? missing : 9.0 for i in 1:200]   # ~75% missing
            
            target_df = DataFrame(timestamp=timestamps, WS_120m=target_speeds)
            source_df = DataFrame(timestamp=timestamps, WS_100m=source_speeds)
            
            target_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")
            source_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")
            
            target_ts = TimeSeriesData(target_df, [target_sensor])
            source_ts = TimeSeriesData(source_df, [source_sensor])
            
            results = analyze_windspeed_correlations(target_ts, source_ts)
            
            # Should return empty due to insufficient concurrent valid data after dropmissing
            @test isempty(results)
        end

        @testset "test_no_speed_sensors" begin
            # No wind speed sensors in target
            timestamps = [DateTime(2023,1,1)]
            target_df = DataFrame(timestamp=timestamps, WD_120m=[180.0])
            source_df = DataFrame(timestamp=timestamps, WS_100m=[10.0])
            
            target_sensors = [SensorColumn(sensorType="WindDirection", statType="avg", height=120.0, columnName=:WD_120m, sensorDirection="N", unit="deg")]
            source_sensors = [SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")]
            
            target_ts = TimeSeriesData(target_df, target_sensors)
            source_ts = TimeSeriesData(source_df, source_sensors)
            
            results = analyze_windspeed_correlations(target_ts, source_ts)
            @test isempty(results)
        end

        @testset "test_zero_variance" begin
            # Constant values (zero variance)
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:149]
            target_speeds = fill(10.0, 150)  # Constant
            source_speeds = fill(8.0, 150)   # Constant
            
            target_df = DataFrame(timestamp=timestamps, WS_120m=target_speeds)
            source_df = DataFrame(timestamp=timestamps, WS_100m=source_speeds)
            
            target_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")
            source_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")
            
            target_ts = TimeSeriesData(target_df, [target_sensor])
            source_ts = TimeSeriesData(source_df, [source_sensor])
            
            results = analyze_windspeed_correlations(target_ts, source_ts)
            
            # Should return empty for zero variance data
            @test isempty(results)
        end

        @testset "test_non_avg_sensors_filtered" begin
            # Include max and min sensors - should only analyze avg
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:149]
            
            Random.seed!(101)
            speeds = 8.0 .+ 4.0 * rand(150)
            
            target_df = DataFrame(
                timestamp=timestamps,
                WS_120m_avg=speeds .* 1.1,
                WS_120m_max=speeds .* 1.3,
                WS_120m_min=speeds .* 0.8
            )
            source_df = DataFrame(
                timestamp=timestamps,
                WS_100m_avg=speeds,
                WS_100m_max=speeds .* 1.2
            )
            
            target_sensors = [
                SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m_avg, sensorDirection="N", unit="m/s"),
                SensorColumn(sensorType="WindSpeed", statType="max", height=120.0, columnName=:WS_120m_max, sensorDirection="N", unit="m/s"),
                SensorColumn(sensorType="WindSpeed", statType="min", height=120.0, columnName=:WS_120m_min, sensorDirection="N", unit="m/s")
            ]
            source_sensors = [
                SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m_avg, sensorDirection="N", unit="m/s"),
                SensorColumn(sensorType="WindSpeed", statType="max", height=100.0, columnName=:WS_100m_max, sensorDirection="N", unit="m/s")
            ]
            
            target_ts = TimeSeriesData(target_df, target_sensors)
            source_ts = TimeSeriesData(source_df, source_sensors)
            
            results = analyze_windspeed_correlations(target_ts, source_ts)
            
            # Should only have 1 pair (avg × avg), not 6 pairs (3 × 2)
            @test length(results) == 1
            @test results[1].target_sensor.statType == "avg"
            @test results[1].source_sensor.statType == "avg"
        end
    end

    @testset "Model Training Tests" begin
        
        @testset "test_train_speed_model_basic" begin
            # Create test data with good speed relationships
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:199]
            
            Random.seed!(202)
            base_speeds = 6.0 .+ 6.0 * rand(200)
            
            # Create pairs with good relationships
            target_120_speeds = base_speeds .* 1.1 .+ 0.2 .+ randn(200) * 0.3  # Good relationship
            source_140_speeds = base_speeds .* 1.02 .+ randn(200) * 0.4  # Good relationship
            
            target_df = DataFrame(
                timestamp=timestamps,
                WS_120m=target_120_speeds
            )
            source_df = DataFrame(
                timestamp=timestamps,
                WS_140m=source_140_speeds
            )
            
            target_sensors = [
                SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")
            ]
            source_sensors = [
                SensorColumn(sensorType="WindSpeed", statType="avg", height=140.0, columnName=:WS_140m, sensorDirection="N", unit="m/s")
            ]
            
            target_ts = TimeSeriesData(target_df, target_sensors)
            source_ts = TimeSeriesData(source_df, source_sensors)
            
            # Train with permissive parameters
            params = CrossMastSpeedTrainParams(
                target_name="Target",
                source_name="Source",
                min_data_points=100,
                min_correlation=0.5,
            )
            
            model = train(CrossMastSpeedModel, params, target_ts, source_ts)
            
            @test model.target_mast_name == "Target"
            @test model.source_mast_name == "Source"
            @test length(model.pairs) == 1  # Should have 1 pair
            
            # Best pair should have high correlation
            @test model.pairs[1].correlation > 0.8
        end

        @testset "test_train_speed_model_filtering" begin
            # Create data with mixed quality relationships
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:199]
            
            Random.seed!(303)
            base_speeds = 7.0 .+ 5.0 * rand(200)
            
            # Good relationship: high correlation, low noise
            good_target = base_speeds .* 1.1 .+ 0.3 .+ randn(200) * 0.2
            good_source = base_speeds .+ randn(200) * 0.3
            
            # Poor relationship: low correlation, high noise  
            poor_target = base_speeds .+ randn(200) * 3.0  # High noise, weak relationship
            poor_source = 5.0 .+ 10.0 * rand(200)  # Independent data
            
            target_df = DataFrame(timestamp=timestamps, WS_good=good_target, WS_poor=poor_target)
            source_df = DataFrame(timestamp=timestamps, WS_good=good_source, WS_poor=poor_source)
            
            target_sensors = [
                SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_good, sensorDirection="N", unit="m/s"),
                SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_poor, sensorDirection="N", unit="m/s")
            ]
            source_sensors = [
                SensorColumn(sensorType="WindSpeed", statType="avg", height=140.0, columnName=:WS_good, sensorDirection="N", unit="m/s"),
                SensorColumn(sensorType="WindSpeed", statType="avg", height=80.0, columnName=:WS_poor, sensorDirection="N", unit="m/s")
            ]
            
            target_ts = TimeSeriesData(target_df, target_sensors)
            source_ts = TimeSeriesData(source_df, source_sensors)
            
            # Train with strict parameters
            strict_params = CrossMastSpeedTrainParams(
                target_name="Target",
                source_name="Source",
                min_data_points=100,
                min_correlation=0.7,  # Should filter out poor relationships
            )
            
            model = train(CrossMastSpeedModel, strict_params, target_ts, source_ts)
            
            # Should only include good relationships that meet criteria
            @test length(model.pairs) <= 2  # Most pairs should be filtered out
            
            # All included pairs should meet criteria
            for pair in model.pairs
                @test pair.correlation >= 0.7
                @test pair.data_points >= 100
            end
        end

        @testset "test_train_speed_model_no_qualified_pairs" begin
            # Create data where no pairs meet strict criteria
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:149]
            
            # All relationships have very poor correlation
            Random.seed!(404)
            target_speeds = 5.0 .+ 10.0 * rand(150)  # Independent random data
            source_speeds = 8.0 .+ 6.0 * rand(150)   # Independent random data
            
            target_df = DataFrame(timestamp=timestamps, WS_120m=target_speeds)
            source_df = DataFrame(timestamp=timestamps, WS_100m=source_speeds)
            
            target_sensors = [SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")]
            source_sensors = [SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")]
            
            target_ts = TimeSeriesData(target_df, target_sensors)
            source_ts = TimeSeriesData(source_df, source_sensors)
            
            # Very strict parameters
            strict_params = CrossMastSpeedTrainParams(
                target_name="Target",
                source_name="Source",
                min_data_points=100,
                min_correlation=0.9   # Very strict
            )
            
            model = train(CrossMastSpeedModel, strict_params, target_ts, source_ts)
            
            @test model.target_mast_name == "Target"
            @test model.source_mast_name == "Source"
            @test isempty(model.pairs)  # No pairs should qualify
        end
    end

    @testset "Model Reconstruction Tests" begin
        
        @testset "test_reconstruct_speed_basic" begin
            # Create a simple model with known relationship
            target_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")
            source_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")
            
            # Model with linear relationship: target = 1.2 * source + 0.5
            pair = CrossMastSpeedPair(
                target_sensor=target_sensor,
                source_sensor=source_sensor,
                correlation=0.95,
                slope=1.2,
                intercept=0.5,
                data_points=200
            )
            
            model = CrossMastSpeedModel(
                target_mast_name="Target",
                source_mast_name="Source",
                pairs=[pair]
            )
            
            # Create source data to reconstruct from
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:9]
            source_speeds = [5.0, 8.0, 10.0, 12.0, 15.0, 7.5, 9.5, 11.5, 13.5, 6.0]
            
            source_df = DataFrame(timestamp=timestamps, WS_100m=source_speeds)
            source_ts = TimeSeriesData(source_df, [source_sensor])
            
            reconstructed_ts = reconstruct(model, source_ts)
            
            @test length(reconstructed_ts.sensors) == 1
            @test reconstructed_ts.sensors[1] == target_sensor
            @test nrow(reconstructed_ts.df) == 10
            
            # Check reconstructed values: should be 1.2 * source + 0.5
            expected_speeds = source_speeds .* 1.2 .+ 0.5
            actual_speeds = reconstructed_ts.df.WS_120m
            
            for (expected, actual) in zip(expected_speeds, actual_speeds)
                @test actual ≈ expected atol=0.001
            end
        end

        @testset "test_reconstruct_speed_bounds_clamping" begin
            # Test that reconstruction clamps to [0, 50] m/s bounds
            target_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")
            source_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")
            
            # Model that could produce values outside bounds
            pair = CrossMastSpeedPair(
                target_sensor=target_sensor,
                source_sensor=source_sensor,
                correlation=0.8,
                slope=2.0,    # High slope
                intercept=-5.0,  # Negative intercept
                data_points=100
            )
            
            model = CrossMastSpeedModel(
                target_mast_name="Target",
                source_mast_name="Source",
                pairs=[pair]
            )
            
            # Source data that would produce out-of-bounds values
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:4]
            source_speeds = [1.0, 30.0, 0.5, 25.0, 2.0]  # Would produce [-3, 55, -4, 45, -1]
            
            source_df = DataFrame(timestamp=timestamps, WS_100m=source_speeds)
            source_ts = TimeSeriesData(source_df, [source_sensor])
            
            reconstructed_ts = reconstruct(model, source_ts)
            
            expected_speeds = [0.0, 50.0, 0.0, 45.0, 0.0]  # Clamped to [0, 50]
            actual_speeds = reconstructed_ts.df.WS_120m
            
            for (expected, actual) in zip(expected_speeds, actual_speeds)
                @test actual ≈ expected atol=0.001
            end
        end

        @testset "test_reconstruct_speed_multiple_pairs" begin
            # Test reconstruction with multiple sensor pairs
            target_120_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")
            target_160_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=160.0, columnName=:WS_160m, sensorDirection="N", unit="m/s")
            source_100_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")
            
            # Two pairs with different target sensors
            pair1 = CrossMastSpeedPair(
                target_sensor=target_120_sensor,
                source_sensor=source_100_sensor,
                correlation=0.85,
                slope=1.1,
                intercept=0.2,
                data_points=150
            )
            
            pair2 = CrossMastSpeedPair(
                target_sensor=target_160_sensor,
                source_sensor=source_100_sensor,
                correlation=0.92,  # Better correlation
                slope=1.15,
                intercept=0.4,
                data_points=150
            )
            
            model = CrossMastSpeedModel(
                target_mast_name="Target",
                source_mast_name="Source",
                pairs=[pair2, pair1]  # Sorted by correlation (pair2 first)
            )
            
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:4]
            source_speeds = [8.0, 10.0, 12.0, 15.0, 6.0]
            
            source_df = DataFrame(timestamp=timestamps, WS_100m=source_speeds)
            source_ts = TimeSeriesData(source_df, [source_100_sensor])
            
            reconstructed_ts = reconstruct(model, source_ts)
            
            @test length(reconstructed_ts.sensors) == 2
            @test nrow(reconstructed_ts.df) == 5
            
            # Check 120m reconstruction: 1.1 * source + 0.2
            expected_120 = source_speeds .* 1.1 .+ 0.2
            actual_120 = reconstructed_ts.df.WS_120m
            for (expected, actual) in zip(expected_120, actual_120)
                @test actual ≈ expected atol=0.001
            end
            
            # Check 160m reconstruction: 1.15 * source + 0.4
            expected_160 = source_speeds .* 1.15 .+ 0.4
            actual_160 = reconstructed_ts.df.WS_160m
            for (expected, actual) in zip(expected_160, actual_160)
                @test actual ≈ expected atol=0.001
            end
        end

        @testset "test_reconstruct_speed_empty_model" begin
            # Test reconstruction with empty model
            model = CrossMastSpeedModel(
                target_mast_name="Target",
                source_mast_name="Source",
                pairs=CrossMastSpeedPair[]
            )
            
            timestamps = [DateTime(2023,1,1)]
            source_df = DataFrame(timestamp=timestamps, WS_100m=[10.0])
            source_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")
            source_ts = TimeSeriesData(source_df, [source_sensor])
            
            reconstructed_ts = reconstruct(model, source_ts)
            
            @test isempty(reconstructed_ts.sensors)
            @test nrow(reconstructed_ts.df) == 1  # Should have timestamps
            @test propertynames(reconstructed_ts.df) == [:timestamp]
        end
    end

    @testset "Integration Tests" begin
        
        @testset "test_complete_analysis_train_reconstruct_workflow" begin
            # Complete workflow from analysis through reconstruction
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:17279]  # 120 days
            
            # Random.seed!(505)
            base_speeds = 3.0 .+ 8.0 * rand(length(timestamps))  # 6-14 m/s range
            
            # Create realistic speed relationships with noise
            target_120_speeds = Vector{Union{Missing, Float64}}(base_speeds .* 1.4 .+ 1.0 .+ 0.5 .* randn(length(timestamps)))
            target_160_speeds = Vector{Union{Missing, Float64}}(base_speeds .* 1.2 .+ 0.5 .+ 0.5 .* randn(length(timestamps)))
            
            source_100_speeds = Vector{Union{Missing, Float64}}(base_speeds)
            source_140_speeds = Vector{Union{Missing, Float64}}(base_speeds .* 1.05 .+ 0.5 .+ 0.5 .* randn(length(timestamps)))
            
            # Add realistic missing data patterns (10% missing per sensor)
            # Simulate different failure patterns: random gaps, maintenance windows
            target_120_speeds[rand(1:length(timestamps), Int(length(timestamps)*0.1))] .= missing  
            target_160_speeds[rand(1:length(timestamps), Int(length(timestamps)*0.1))] .= missing  
            source_100_speeds[rand(1:length(timestamps), Int(length(timestamps)*0.1))] .= missing  
            source_140_speeds[rand(1:length(timestamps), Int(length(timestamps)*0.1))] .= missing  
            
            target_df = DataFrame(
                timestamp=timestamps,
                WS_120m=target_120_speeds,
                WS_160m=target_160_speeds
            )
            source_df = DataFrame(
                timestamp=timestamps,
                WS_100m=source_100_speeds,
                WS_140m=source_140_speeds
            )
            
            target_sensors = [
                SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s"),
                SensorColumn(sensorType="WindSpeed", statType="avg", height=160.0, columnName=:WS_160m, sensorDirection="N", unit="m/s")
            ]
            source_sensors = [
                SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s"),
                SensorColumn(sensorType="WindSpeed", statType="avg", height=140.0, columnName=:WS_140m, sensorDirection="N", unit="m/s")
            ]
            
            target_ts = TimeSeriesData(target_df, target_sensors)
            source_ts = TimeSeriesData(source_df, source_sensors)
            
            # Train model with reasonable parameters
            params = CrossMastSpeedTrainParams(
                target_name="TestTarget",
                source_name="TestSource",
                min_data_points=200,
                min_correlation=0.7,
            )
            
            model = train(CrossMastSpeedModel, params, target_ts, source_ts)
            @test length(model.pairs) == 4
            @test model.target_mast_name == "TestTarget"
            @test model.source_mast_name == "TestSource"
            
            # Test that trained model parameters match the designed relationships
            # Expected relationships from our test data construction:
            expected_relationships = Dict(
                (120.0, 100.0) => (slope=1.4, intercept=1.0),           # target_120 vs source_100
                (160.0, 100.0) => (slope=1.2, intercept=0.5),           # target_160 vs source_100  
            )
            
            for pair in model.pairs
                target_height = pair.target_sensor.height
                source_height = pair.source_sensor.height
                key = (target_height, source_height)
                if (key in keys(expected_relationships))
                    expected = expected_relationships[key]
                    # Allow reasonable tolerance for slope and intercept given noise levels
                    @test pair.slope ≈ expected.slope atol=0.05  # ±0.05 tolerance for slope
                    @test pair.intercept ≈ expected.intercept atol=0.1  # ±0.1 m/s tolerance for intercept
                    
                    # Verify the model learned reasonable correlations
                    @test pair.correlation > 0.7  # Should detect strong relationships (r² = 0.7² = 0.49)
                end
            end
            
            # Step 3: Reconstruct using the trained model
            reconstructed_ts = reconstruct(model, source_ts)
            @test !isempty(reconstructed_ts.sensors)
            @test nrow(reconstructed_ts.df) == length(timestamps)
            
            # Verify reconstruction quality by comparing statistical properties (mean speeds by layer)
            for pair in model.pairs
                target_col = pair.target_sensor.columnName
                source_col = pair.source_sensor.columnName
                
                # Get all reconstructed and source values (collect to get actual vectors)
                source_vals = filter(!ismissing, source_ts.df[!, source_col])
                reconstructed_vals = filter(!ismissing, reconstructed_ts.df[!, target_col])
                
                if length(source_vals) > 50 && length(reconstructed_vals) > 50
                    # Compare mean speeds (should follow linear relationship statistically)
                    mean_source = mean(source_vals)
                    mean_reconstructed = mean(reconstructed_vals)
                    expected_mean = clamp(pair.slope * mean_source + pair.intercept, 0.0, 50.0)
                    
                    # Allow for reasonable tolerance based on the noise in training data (~0.3-0.5 m/s)
                    @test mean_reconstructed ≈ expected_mean atol=0.05  # ±0.05 m/s tolerance for noisy data
                    
                    # Verify reconstruction preserves wind speed ranges (no extreme outliers)
                    @test all(v -> 0.0 <= v <= 50.0, reconstructed_vals)  # Within physical bounds
                    @test std(reconstructed_vals) > 0.1  # Should have reasonable variance
                end
            end
        end
    end
end

# Helper Functions for Testing
"""
    create_speed_test_data(start_time, num_intervals, base_speeds, slope, intercept, noise_std)

Create test speed data with specified linear relationship and noise characteristics.
"""
function create_speed_test_data(start_time::DateTime, num_intervals::Int,
                               base_speeds::Vector{Float64}, slope::Float64, 
                               intercept::Float64, noise_std::Float64)
    timestamps = [start_time + Minute(10*i) for i in 0:num_intervals-1]
    Random.seed!(42)  # For reproducible tests
    speeds = clamp.(base_speeds .* slope .+ intercept .+ randn(num_intervals) * noise_std, 0.0, 50.0)
    return timestamps, speeds
end

"""
    validate_linear_relationship(target_vals, source_vals, expected_slope, expected_intercept, tolerance=0.1)

Validate that linear relationship was detected correctly.
"""
function validate_linear_relationship(target_vals::Vector{Float64}, source_vals::Vector{Float64}, 
                                    expected_slope::Float64, expected_intercept::Float64, tolerance::Float64=0.1)
    # Simple linear regression to check relationship
    n = length(target_vals)
    sum_x = sum(source_vals)
    sum_y = sum(target_vals)
    sum_xy = sum(source_vals .* target_vals)
    sum_x2 = sum(source_vals .^ 2)
    
    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x^2)
    intercept = (sum_y - slope * sum_x) / n
    
    @test abs(slope - expected_slope) <= tolerance
    @test abs(intercept - expected_intercept) <= tolerance
end

@testset "Helper Function Tests" begin
    @testset "test_helper_functions" begin
        # Test create_speed_test_data
        base_speeds = [8.0, 10.0, 12.0, 9.0]
        timestamps, speeds = create_speed_test_data(DateTime(2023,1,1), 4, base_speeds, 1.1, 0.5, 0.1)
        
        @test length(timestamps) == 4
        @test length(speeds) == 4
        @test all(s -> 0.0 <= s <= 50.0, speeds)  # Should be within bounds
        
        # Test validate_linear_relationship
        source_vals = [5.0, 10.0, 15.0, 20.0]
        target_vals = source_vals .* 1.2 .+ 0.8  # Perfect linear relationship
        validate_linear_relationship(target_vals, source_vals, 1.2, 0.8, 0.01)
    end
end 