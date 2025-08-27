"""
    test_cross_mast_summary.jl

Comprehensive test suite for CrossMastSummary.jl module in cross-mast reconstruction system.
Tests summary statistics generation and high-elevation filtering functions.
"""

using Test
using DataFrames
using Dates
using Statistics
using Random

# Import the modules we need to test
using CleanMastProject.TrainReconstructCross.CrossMastSummary
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.Types.CrossMastSpeedModels: CrossMastSpeedPair
using CleanMastProject.Types.CrossMastDirectionModels: CrossMastDirectionPair
using CleanMastProject.Types.CrossMastAnalysisResults: CorrelationSummary, DirectionSummary

@testset "CrossMastSummary.jl Tests" begin

    @testset "Speed Correlation Summary Tests" begin
        
        @testset "test_summarize_correlations_mixed_elevations" begin
            # Create test data with mix of high and low elevation sensors
            target_120_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")
            target_160_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=160.0, columnName=:WS_160m, sensorDirection="N", unit="m/s")
            target_80_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=80.0, columnName=:WS_80m, sensorDirection="N", unit="m/s")
            
            source_140_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=140.0, columnName=:WS_140m, sensorDirection="N", unit="m/s")
            source_100_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")
            
            correlations = [
                # High elevation pairs (both ≥120m)
                CrossMastSpeedPair(target_sensor=target_120_sensor, source_sensor=source_140_sensor, slope=1.1, intercept=0.2, correlation=0.85, data_points=200),  # High elevation
                CrossMastSpeedPair(target_sensor=target_160_sensor, source_sensor=source_140_sensor, slope=1.15, intercept=0.3, correlation=0.92, data_points=250), # High elevation, best
                
                # Mixed elevation pairs (one <120m)
                CrossMastSpeedPair(target_sensor=target_120_sensor, source_sensor=source_100_sensor, slope=1.05, intercept=0.1, correlation=0.78, data_points=180),
                CrossMastSpeedPair(target_sensor=target_80_sensor, source_sensor=source_140_sensor, slope=0.95, intercept=-0.1, correlation=0.75, data_points=190)
            ]
            
            summary = summarize_correlations(correlations)
            
            @test summary.total_pairs == 4
            @test summary.high_elevation_pairs == 2  # Only 2 pairs where both sensors ≥120m
            @test summary.best_correlation ≈ 0.92   # Best overall
            @test summary.best_high_elevation_correlation ≈ 0.92  # Best among high elevation
            
            # Average high elevation correlation should be (0.85 + 0.92) / 2 = 0.885
            expected_high_avg = (0.85 + 0.92) / 2
            @test summary.average_high_elevation_correlation ≈ expected_high_avg atol=0.001
        end

        @testset "test_summarize_correlations_no_high_elevation" begin
            # Test case with no high elevation pairs
            target_80_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=80.0, columnName=:WS_80m, sensorDirection="N", unit="m/s")
            target_100_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")
            
            source_60_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=60.0, columnName=:WS_60m, sensorDirection="N", unit="m/s")
            source_90_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=90.0, columnName=:WS_90m, sensorDirection="N", unit="m/s")
            
            correlations = [
                CrossMastSpeedPair(target_sensor=target_80_sensor, source_sensor=source_60_sensor, slope=0.95, intercept=0.1, correlation=0.75, data_points=150),
                CrossMastSpeedPair(target_sensor=target_100_sensor, source_sensor=source_90_sensor, slope=1.02, intercept=0.3, correlation=0.82, data_points=180)
            ]
            
            summary = summarize_correlations(correlations)
            
            @test summary.total_pairs == 2
            @test summary.high_elevation_pairs == 0  # No pairs where both sensors ≥120m
            @test summary.best_correlation ≈ 0.82
            @test summary.best_high_elevation_correlation ≈ 0.0  # No high elevation pairs
            @test summary.average_high_elevation_correlation ≈ 0.0  # No high elevation pairs
        end

        @testset "test_summarize_correlations_empty" begin
            # Test with empty correlation list
            summary = summarize_correlations(CrossMastSpeedPair[])
            
            @test summary.total_pairs == 0
            @test summary.high_elevation_pairs == 0
            @test summary.best_correlation ≈ 0.0
            @test summary.best_high_elevation_correlation ≈ 0.0
            @test summary.average_high_elevation_correlation ≈ 0.0
        end

        @testset "test_get_best_high_elevation_correlation" begin
            # Test high elevation filtering function directly
            target_120_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")
            target_160_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=160.0, columnName=:WS_160m, sensorDirection="N", unit="m/s")
            target_80_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=80.0, columnName=:WS_80m, sensorDirection="N", unit="m/s")
            
            source_140_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=140.0, columnName=:WS_140m, sensorDirection="N", unit="m/s")
            source_100_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")
            
            correlations = [
                # High elevation pair
                CrossMastSpeedPair(target_sensor=target_160_sensor, source_sensor=source_140_sensor, slope=1.15, intercept=0.3, correlation=0.88, data_points=200),
                
                # Mixed elevation pairs (should be excluded)
                CrossMastSpeedPair(target_sensor=target_120_sensor, source_sensor=source_100_sensor, slope=1.05, intercept=0.1, correlation=0.95, data_points=180),  # Higher correlation but low source
                CrossMastSpeedPair(target_sensor=target_80_sensor, source_sensor=source_140_sensor, slope=0.95, intercept=-0.1, correlation=0.85, data_points=190),  # Low target
                
                # Another high elevation pair
                CrossMastSpeedPair(target_sensor=target_120_sensor, source_sensor=source_140_sensor, slope=1.1, intercept=0.2, correlation=0.82, data_points=200)
            ]
            
            best_high_corr = get_best_high_elevation_correlation(correlations)
            @test best_high_corr ≈ 0.88  # Best among high elevation pairs only
            
            # Test with no high elevation pairs
            low_elevation_correlations = [
                CrossMastSpeedPair(target_sensor=target_80_sensor, source_sensor=source_100_sensor, slope=0.98, intercept=0.05, correlation=0.90, data_points=160)
            ]
            best_low_corr = get_best_high_elevation_correlation(low_elevation_correlations)
            @test best_low_corr ≈ 0.0
            
            # Test with empty list
            empty_corr = get_best_high_elevation_correlation(CrossMastSpeedPair[])
            @test empty_corr ≈ 0.0
        end
    end

    @testset "Direction Analysis Summary Tests" begin
        
        @testset "test_summarize_direction_analysis_mixed_elevations" begin
            # Create test data with mix of high and low elevation sensors
            target_120_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=120.0, columnName=:WD_120m, sensorDirection="N", unit="deg")
            target_160_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=160.0, columnName=:WD_160m, sensorDirection="N", unit="deg")
            target_80_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=80.0, columnName=:WD_80m, sensorDirection="N", unit="deg")
            
            source_140_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=140.0, columnName=:WD_140m, sensorDirection="N", unit="deg")
            source_100_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=100.0, columnName=:WD_100m, sensorDirection="N", unit="deg")
            
            direction_results = [
                # High elevation pairs (both ≥120m)
                CrossMastDirectionPair(target_120_sensor, source_140_sensor, 5.0, 8.5, 200),  # High elevation
                CrossMastDirectionPair(target_160_sensor, source_140_sensor, 3.2, 6.1, 250), # High elevation, best std
                
                # Mixed elevation pairs (one <120m)
                CrossMastDirectionPair(target_120_sensor, source_100_sensor, 8.1, 12.3, 180),
                CrossMastDirectionPair(target_80_sensor, source_140_sensor, -2.5, 9.8, 190)
            ]
            
            summary = summarize_direction_analysis(direction_results)
            
            @test summary.total_pairs == 4
            @test summary.high_elevation_pairs == 2  # Only 2 pairs where both sensors ≥120m
            @test summary.best_std_deviation ≈ 6.1   # Best overall std deviation
            @test summary.best_high_elevation_std ≈ 6.1  # Best among high elevation pairs
        end

        @testset "test_summarize_direction_analysis_no_high_elevation" begin
            # Test case with no high elevation pairs
            target_80_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=80.0, columnName=:WD_80m, sensorDirection="N", unit="deg")
            target_100_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=100.0, columnName=:WD_100m, sensorDirection="N", unit="deg")
            
            source_60_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=60.0, columnName=:WD_60m, sensorDirection="N", unit="deg")
            source_90_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=90.0, columnName=:WD_90m, sensorDirection="N", unit="deg")
            
            direction_results = [
                CrossMastDirectionPair(target_80_sensor, source_60_sensor, 12.5, 15.2, 150),
                CrossMastDirectionPair(target_100_sensor, source_90_sensor, -5.8, 11.7, 180)
            ]
            
            summary = summarize_direction_analysis(direction_results)
            
            @test summary.total_pairs == 2
            @test summary.high_elevation_pairs == 0  # No pairs where both sensors ≥120m
            @test summary.best_std_deviation ≈ 11.7
            @test summary.best_high_elevation_std == Inf  # No high elevation pairs
        end

        @testset "test_summarize_direction_analysis_empty" begin
            # Test with empty direction results list
            summary = summarize_direction_analysis(CrossMastDirectionPair[])
            
            @test summary.total_pairs == 0
            @test summary.high_elevation_pairs == 0
            @test summary.best_std_deviation == Inf
            @test summary.best_high_elevation_std == Inf
        end

        @testset "test_get_best_high_elevation_direction_std" begin
            # Test high elevation filtering function directly
            target_120_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=120.0, columnName=:WD_120m, sensorDirection="N", unit="deg")
            target_160_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=160.0, columnName=:WD_160m, sensorDirection="N", unit="deg")
            target_80_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=80.0, columnName=:WD_80m, sensorDirection="N", unit="deg")
            
            source_140_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=140.0, columnName=:WD_140m, sensorDirection="N", unit="deg")
            source_100_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=100.0, columnName=:WD_100m, sensorDirection="N", unit="deg")
            
            direction_results = [
                # High elevation pairs
                CrossMastDirectionPair(target_160_sensor, source_140_sensor, 3.2, 7.8, 200),  # Best std among high elevation
                CrossMastDirectionPair(target_120_sensor, source_140_sensor, 5.1, 9.5, 200),
                
                # Mixed elevation pairs (should be excluded)
                CrossMastDirectionPair(target_120_sensor, source_100_sensor, 2.5, 5.2, 180),  # Better std but low source
                CrossMastDirectionPair(target_80_sensor, source_140_sensor, -1.8, 4.1, 190)  # Better std but low target
            ]
            
            best_high_std = get_best_high_elevation_direction_std(direction_results)
            @test best_high_std ≈ 7.8  # Best (minimum) std among high elevation pairs only
            
            # Test with no high elevation pairs
            low_elevation_results = [
                CrossMastDirectionPair(target_80_sensor, source_100_sensor, 8.5, 12.1, 160)
            ]
            best_low_std = get_best_high_elevation_direction_std(low_elevation_results)
            @test best_low_std == Inf
            
            # Test with empty list
            empty_std = get_best_high_elevation_direction_std(CrossMastDirectionPair[])
            @test empty_std == Inf
        end
    end

    @testset "High Elevation Filtering Tests" begin
        
        @testset "test_high_elevation_boundary_120m" begin
            # Test the exact 120m boundary for high elevation classification
            target_119_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=119.9, columnName=:WS_119m, sensorDirection="N", unit="m/s")
            target_120_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")
            target_121_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=120.1, columnName=:WS_121m, sensorDirection="N", unit="m/s")
            
            source_120_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m_src, sensorDirection="N", unit="m/s")
            
            correlations = [
                CrossMastSpeedPair(target_sensor=target_119_sensor, source_sensor=source_120_sensor, slope=1.0, intercept=0.0, correlation=0.85, data_points=200),  # Should NOT qualify (119.9 < 120)
                CrossMastSpeedPair(target_sensor=target_120_sensor, source_sensor=source_120_sensor, slope=1.0, intercept=0.0, correlation=0.80, data_points=200),  # Should qualify (120.0 >= 120)
                CrossMastSpeedPair(target_sensor=target_121_sensor, source_sensor=source_120_sensor, slope=1.0, intercept=0.0, correlation=0.90, data_points=200)   # Should qualify (120.1 >= 120)
            ]
            
            summary = summarize_correlations(correlations)
            
            @test summary.total_pairs == 3
            @test summary.high_elevation_pairs == 2  # Only pairs 2 and 3 qualify
            @test summary.best_high_elevation_correlation ≈ 0.90  # Best among qualifying pairs
            
            expected_high_avg = (0.80 + 0.90) / 2  # Average of qualifying pairs
            @test summary.average_high_elevation_correlation ≈ expected_high_avg atol=0.001
        end

        @testset "test_both_sensors_must_be_high_elevation" begin
            # Test that BOTH sensors must be ≥120m for high elevation classification
            target_140_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=140.0, columnName=:WS_140m, sensorDirection="N", unit="m/s")
            target_100_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")
            
            source_130_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=130.0, columnName=:WS_130m, sensorDirection="N", unit="m/s")
            source_110_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=110.0, columnName=:WS_110m, sensorDirection="N", unit="m/s")
            
            correlations = [
                CrossMastSpeedPair(target_sensor=target_140_sensor, source_sensor=source_130_sensor, slope=1.1, intercept=0.2, correlation=0.88, data_points=200),  # Both high: QUALIFIES
                CrossMastSpeedPair(target_sensor=target_140_sensor, source_sensor=source_110_sensor, slope=1.05, intercept=0.1, correlation=0.85, data_points=180), # High target, low source: NO
                CrossMastSpeedPair(target_sensor=target_100_sensor, source_sensor=source_130_sensor, slope=0.95, intercept=-0.1, correlation=0.82, data_points=190), # Low target, high source: NO
                CrossMastSpeedPair(target_sensor=target_100_sensor, source_sensor=source_110_sensor, slope=0.98, intercept=0.05, correlation=0.75, data_points=160)  # Both low: NO
            ]
            
            summary = summarize_correlations(correlations)
            
            @test summary.total_pairs == 4
            @test summary.high_elevation_pairs == 1  # Only first pair qualifies
            @test summary.best_high_elevation_correlation ≈ 0.88
            @test summary.average_high_elevation_correlation ≈ 0.88  # Only one qualifying pair
        end
    end

    @testset "Summary Statistics Validation Tests" begin
        
        @testset "test_correlation_summary_field_validation" begin
            # Test that all summary fields have expected properties
            target_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=140.0, columnName=:WS_140m, sensorDirection="N", unit="m/s")
            source_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=130.0, columnName=:WS_130m, sensorDirection="N", unit="m/s")
            
            correlations = [
                CrossMastSpeedPair(target_sensor=target_sensor, source_sensor=source_sensor, slope=1.1, intercept=0.2, correlation=0.75, data_points=150),
                CrossMastSpeedPair(target_sensor=target_sensor, source_sensor=source_sensor, slope=1.05, intercept=0.1, correlation=0.82, data_points=180),
                CrossMastSpeedPair(target_sensor=target_sensor, source_sensor=source_sensor, slope=1.15, intercept=0.3, correlation=0.88, data_points=200)
            ]
            
            summary = summarize_correlations(correlations)
            
            # Validate field ranges and relationships
            @test summary.total_pairs >= 0
            @test summary.high_elevation_pairs >= 0
            @test summary.high_elevation_pairs <= summary.total_pairs
            
            @test 0.0 <= summary.best_correlation <= 1.0
            @test 0.0 <= summary.best_high_elevation_correlation <= 1.0
            @test 0.0 <= summary.average_high_elevation_correlation <= 1.0
            
            @test summary.best_correlation >= summary.average_high_elevation_correlation  # Best should be ≥ average
            @test summary.best_high_elevation_correlation >= summary.average_high_elevation_correlation  # Best should be ≥ average
        end

        @testset "test_direction_summary_field_validation" begin
            # Test that all direction summary fields have expected properties
            target_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=140.0, columnName=:WD_140m, sensorDirection="N", unit="deg")
            source_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=130.0, columnName=:WD_130m, sensorDirection="N", unit="deg")
            
            direction_results = [
                CrossMastDirectionPair(target_sensor, source_sensor, 5.2, 12.5, 150),
                CrossMastDirectionPair(target_sensor, source_sensor, -3.8, 8.9, 180),
                CrossMastDirectionPair(target_sensor, source_sensor, 1.5, 15.2, 200)
            ]
            
            summary = summarize_direction_analysis(direction_results)
            
            # Validate field ranges and relationships
            @test summary.total_pairs >= 0
            @test summary.high_elevation_pairs >= 0
            @test summary.high_elevation_pairs <= summary.total_pairs
            
            @test summary.best_std_deviation >= 0.0  # Standard deviation is always non-negative
            @test summary.best_high_elevation_std >= 0.0 || summary.best_high_elevation_std == Inf
            
            @test summary.best_std_deviation <= summary.best_high_elevation_std || summary.best_high_elevation_std == Inf  # Best overall ≤ best high elevation
        end
    end

    @testset "Performance and Edge Cases Tests" begin
        
        @testset "test_large_dataset_performance" begin
            # Test with large number of sensor pairs
            correlations = CrossMastSpeedPair[]
            
            Random.seed!(606)
            for i in 1:1000
                target_height = 80.0 + rand() * 100.0  # 80-180m range
                source_height = 60.0 + rand() * 120.0  # 60-180m range
                
                target_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=target_height, columnName=Symbol("WS_target_$i"), sensorDirection="N", unit="m/s")
                source_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=source_height, columnName=Symbol("WS_source_$i"), sensorDirection="N", unit="m/s")
                
                correlation = 0.3 + rand() * 0.6  # 0.3-0.9 range
                
                pair = CrossMastSpeedPair(target_sensor=target_sensor, source_sensor=source_sensor, slope=1.0, intercept=0.0, correlation=correlation, data_points=200)
                push!(correlations, pair)
            end
            
            # Performance test
            @time summary = summarize_correlations(correlations)
            
            @test summary.total_pairs == 1000
            @test summary.high_elevation_pairs <= 1000  # Should be reasonable subset
            @test summary.high_elevation_pairs >= 0
            @test 0.3 <= summary.best_correlation <= 0.9  # Within expected range
        end

        @testset "test_identical_correlations" begin
            # Test case where all correlations are identical
            target_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=140.0, columnName=:WS_140m, sensorDirection="N", unit="m/s")
            source_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=130.0, columnName=:WS_130m, sensorDirection="N", unit="m/s")
            
            correlations = [
                CrossMastSpeedPair(target_sensor=target_sensor, source_sensor=source_sensor, slope=1.1, intercept=0.2, correlation=0.80, data_points=150),
                CrossMastSpeedPair(target_sensor=target_sensor, source_sensor=source_sensor, slope=1.1, intercept=0.2, correlation=0.80, data_points=150),
                CrossMastSpeedPair(target_sensor=target_sensor, source_sensor=source_sensor, slope=1.1, intercept=0.2, correlation=0.80, data_points=150)
            ]
            
            summary = summarize_correlations(correlations)
            
            @test summary.total_pairs == 3
            @test summary.high_elevation_pairs == 3  # All are high elevation
            @test summary.best_correlation ≈ 0.80
            @test summary.best_high_elevation_correlation ≈ 0.80
            @test summary.average_high_elevation_correlation ≈ 0.80  # All identical
        end
    end
end

# Helper Functions for Testing
"""
    create_test_speed_pair(target_height, source_height, correlation, data_points=200)

Create a test CrossMastSpeedPair with specified sensor heights and correlation.
"""
function create_test_speed_pair(target_height::Float64, source_height::Float64, 
                               correlation::Float64, data_points::Int=200)
    target_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=target_height, 
                                columnName=Symbol("WS_$(Int(target_height))m"), sensorDirection="N", unit="m/s")
    source_sensor = SensorColumn(sensorType="WindSpeed", statType="avg", height=source_height,
                                columnName=Symbol("WS_$(Int(source_height))m"), sensorDirection="N", unit="m/s")
    
    return CrossMastSpeedPair(target_sensor=target_sensor, source_sensor=source_sensor, slope=1.0, intercept=0.0, correlation=correlation, data_points=data_points)
end

"""
    create_test_direction_pair(target_height, source_height, std_deviation, data_points=200)

Create a test CrossMastDirectionPair with specified sensor heights and standard deviation.
"""
function create_test_direction_pair(target_height::Float64, source_height::Float64,
                                  std_deviation::Float64, data_points::Int=200)
    target_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=target_height,
                                columnName=Symbol("WD_$(Int(target_height))m"), sensorDirection="N", unit="deg")
    source_sensor = SensorColumn(sensorType="WindDirection", statType="avg", height=source_height,
                                columnName=Symbol("WD_$(Int(source_height))m"), sensorDirection="N", unit="deg")
    
    return CrossMastDirectionPair(target_sensor, source_sensor, 0.0, std_deviation, data_points)
end

@testset "Helper Function Tests" begin
    @testset "test_helper_functions" begin
        # Test create_test_speed_pair
        speed_pair = create_test_speed_pair(120.0, 100.0, 0.85, 150)
        @test speed_pair.target_sensor.height == 120.0
        @test speed_pair.source_sensor.height == 100.0
        @test speed_pair.correlation ≈ 0.85
        @test speed_pair.data_points == 150
        
        # Test create_test_direction_pair
        direction_pair = create_test_direction_pair(140.0, 130.0, 8.5, 200)
        @test direction_pair.target_sensor.height == 140.0
        @test direction_pair.source_sensor.height == 130.0
        @test direction_pair.std_deviation ≈ 8.5
        @test direction_pair.data_points == 200
    end
end 