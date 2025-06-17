using Test
using DataFrames
using Dates
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, SensorColumn
using CleanMastProject.Types.AnalyzeReconstructSingleConfiguration: ProcessedMastReconstructConfig
using CleanMastProject.AnalyzeReconstructSingle.DataCoverage: calculate_coverage_stats
using CleanMastProject.AnalyzeReconstructSingle.WindSpeedCorrelation: calculate_r2_matrix
using CleanMastProject.AnalyzeReconstructSingle.WindDirectionDifference: circular_mean_difference, circular_std_difference

@testset "Analyze Reconstruct Single Tests" begin
    # Create test data
    timestamps = DateTime(2024, 1, 1):Minute(10):DateTime(2024, 1, 1, 2, 0)
    n = length(timestamps)
    
    # Create sensors
    sensors = [
        SensorColumn("WS_100m_avg", "WindSpeed", 100.0, "avg", 1),
        SensorColumn("WS_80m_avg", "WindSpeed", 80.0, "avg", 2),
        SensorColumn("WD_100m_avg", "WindDirection", 100.0, "avg", 3),
        SensorColumn("WD_80m_avg", "WindDirection", 80.0, "avg", 4)
    ]
    
    # Create before data with some missing values
    before_df = DataFrame(
        timestamp = timestamps,
        WS_100m_avg = [i % 3 == 0 ? missing : 10.0 + randn() for i in 1:n],
        WS_80m_avg = [i % 4 == 0 ? missing : 8.0 + randn() for i in 1:n],
        WD_100m_avg = [i % 5 == 0 ? missing : 180.0 + 10*randn() for i in 1:n],
        WD_80m_avg = [i % 6 == 0 ? missing : 175.0 + 10*randn() for i in 1:n]
    )
    
    # Create after data with fewer missing values (simulating reconstruction)
    after_df = DataFrame(
        timestamp = timestamps,
        WS_100m_avg = [i % 9 == 0 ? missing : 10.0 + randn() for i in 1:n],
        WS_80m_avg = [i % 12 == 0 ? missing : 8.0 + randn() for i in 1:n],
        WD_100m_avg = [i % 15 == 0 ? missing : 180.0 + 10*randn() for i in 1:n],
        WD_80m_avg = [i % 18 == 0 ? missing : 175.0 + 10*randn() for i in 1:n]
    )
    
    before_data = TimeSeriesData(before_df, sensors)
    after_data = TimeSeriesData(after_df, sensors)
    
    @testset "Data Coverage Analysis" begin
        stats = calculate_coverage_stats(before_data, after_data)
        
        @test length(stats) == 4
        @test all(s -> s.totalPoints == n, stats)
        @test all(s -> s.missingAfter <= s.missingBefore, stats)
        @test all(s -> 0 <= s.reconstructionRate <= 100, stats)
        @test all(s -> 0 <= s.coverageRatioAfter <= 100, stats)
    end
    
    @testset "Wind Speed Correlation" begin
        r2_matrix, heights, r2_df = calculate_r2_matrix(after_data)
        
        @test size(r2_matrix) == (2, 2)
        @test heights == [80.0, 100.0]
        @test r2_matrix[1, 1] ≈ 1.0
        @test r2_matrix[2, 2] ≈ 1.0
        @test 0 <= r2_matrix[1, 2] <= 1.0 || isnan(r2_matrix[1, 2])
    end
    
    @testset "Wind Direction Difference" begin
        # Test circular mean difference
        angles1 = [350.0, 10.0, 180.0]
        angles2 = [355.0, 5.0, 185.0]
        mean_diff = circular_mean_difference(angles1, angles2)
        @test abs(mean_diff) < 10.0
        
        # Test circular std difference
        std_diff = circular_std_difference(angles1, angles2)
        @test std_diff >= 0.0
        
        # Test edge cases
        angles3 = [359.0, 1.0]
        angles4 = [1.0, 359.0]
        mean_diff2 = circular_mean_difference(angles3, angles4)
        @test abs(mean_diff2) < 5.0
    end
end 