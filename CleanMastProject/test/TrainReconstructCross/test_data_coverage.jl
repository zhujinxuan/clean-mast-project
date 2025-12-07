"""
    test_data_coverage.jl

Comprehensive test suite for DataCoverage.jl module in cross-mast reconstruction system.
Tests time series overlap analysis, highest sensor selection, and day calculations.
"""

using Test
using DataFrames
using Dates
using Statistics
using Random

# Import the modules we need to test
using CleanMastProject.TrainReconstructCross.DataCoverage
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.Types.CrossMastAnalysisResults: MastPairCoverage, from_dict, to_dict

@testset "DataCoverage.jl Tests" begin

    @testset "Core Functionality Tests" begin
        
        @testset "test_highest_sensor_selection" begin
            # Multiple sensors at different heights
            sensors = [
                SensorColumn(sensorType="WindSpeed", statType="avg", height=40.0, columnName=:WS_40m, sensorDirection="N", unit="m/s"),
                SensorColumn(sensorType="WindSpeed", statType="avg", height=80.0, columnName=:WS_80m, sensorDirection="N", unit="m/s"), 
                SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s"),
                SensorColumn(sensorType="WindSpeed", statType="avg", height=160.0, columnName=:WS_160m, sensorDirection="N", unit="m/s")
            ]
            highest = find_highest_wind_speed_sensor(sensors)
            @test highest.height == 160.0
            @test highest.columnName == :WS_160m

            # Only one wind speed sensor
            sensors_single = [SensorColumn(sensorType="WindSpeed", statType="avg", height=80.0, columnName=:WS_80m, sensorDirection="N", unit="m/s")]
            highest_single = find_highest_wind_speed_sensor(sensors_single)
            @test highest_single.height == 80.0

            # No wind speed sensors
            sensors_empty = [SensorColumn(sensorType="WindDirection", statType="avg", height=120.0, columnName=:WD_120m, sensorDirection="N", unit="deg")]
            highest_none = find_highest_wind_speed_sensor(sensors_empty)
            @test isnothing(highest_none)

            # Mixed statTypes (should only select "avg")
            sensors_mixed = [
                SensorColumn(sensorType="WindSpeed", statType="max", height=160.0, columnName=:WS_160m_max, sensorDirection="N", unit="m/s"),
                SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m_avg, sensorDirection="N", unit="m/s")
            ]
            highest_mixed = find_highest_wind_speed_sensor(sensors_mixed)
            @test highest_mixed.height == 120.0  # Should pick avg, not max
        end

        @testset "test_valid_timestamps_extraction" begin
            # Create test dataframe with mixed missing/valid data
            df = DataFrame(
                timestamp = [DateTime(2023,1,1,0,0), DateTime(2023,1,1,0,10), DateTime(2023,1,1,0,20), DateTime(2023,1,1,0,30)],
                WS_120m = [12.5, missing, 14.2, 13.8]
            )

            valid_timestamps = get_valid_timestamps(df, :WS_120m)
            @test length(valid_timestamps) == 3  # Should exclude the missing value
            @test DateTime(2023,1,1,0,10) ∉ valid_timestamps  # Missing value timestamp excluded

            # All missing data
            df_all_missing = DataFrame(
                timestamp = [DateTime(2023,1,1,0,0), DateTime(2023,1,1,0,10)],
                WS_120m = [missing, missing]
            )
            valid_timestamps_empty = get_valid_timestamps(df_all_missing, :WS_120m)
            @test isempty(valid_timestamps_empty)

            # All valid data
            df_all_valid = DataFrame(
                timestamp = [DateTime(2023,1,1,0,0), DateTime(2023,1,1,0,10), DateTime(2023,1,1,0,20)],
                WS_120m = [12.5, 13.0, 14.2]
            )
            valid_timestamps_all = get_valid_timestamps(df_all_valid, :WS_120m)
            @test length(valid_timestamps_all) == 3

            # Column doesn't exist
            valid_timestamps_no_col = get_valid_timestamps(df, :NonexistentColumn)
            @test isempty(valid_timestamps_no_col)
        end

        @testset "test_10_minute_interval_day_calculation" begin
            # Exact 1 day = 144 intervals (24 hours * 6 intervals/hour)
            concurrent_records_1_day = 144
            expected_days_1 = (concurrent_records_1_day * 10.0) / (60.0 * 24.0)
            @test expected_days_1 ≈ 1.0 atol=0.01

            # Exact 7 days
            concurrent_records_7_days = 144 * 7
            expected_days_7 = (concurrent_records_7_days * 10.0) / (60.0 * 24.0)
            @test expected_days_7 ≈ 7.0 atol=0.01

            # 15 days = 2,160 intervals (15 * 24 * 6)
            concurrent_records_15_days = 2160
            expected_days_15 = (concurrent_records_15_days * 10.0) / (60.0 * 24.0)
            @test expected_days_15 ≈ 15.0 atol=0.01

            # Edge case: 1 interval = 10 minutes
            concurrent_records_1 = 1
            expected_days_tiny = (concurrent_records_1 * 10.0) / (60.0 * 24.0)
            @test expected_days_tiny ≈ 0.00694 atol=0.001  # 10 minutes ≈ 0.00694 days
        end

        @testset "test_potential_timestamps_calculation" begin
            # Exact 1 day = 1440 minutes = 144 intervals
            start_time = DateTime(2023, 1, 1, 0, 0)
            end_time = DateTime(2023, 1, 2, 0, 0)
            potential = calculate_potential_timestamps(start_time, end_time)
            @test potential == 144

            # Exact 1 hour = 60 minutes = 6 intervals  
            start_hour = DateTime(2023, 1, 1, 12, 0)
            end_hour = DateTime(2023, 1, 1, 13, 0)
            potential_hour = calculate_potential_timestamps(start_hour, end_hour)
            @test potential_hour == 6

            # 25 minutes = 2 intervals (floor division)
            start_25min = DateTime(2023, 1, 1, 12, 0)
            end_25min = DateTime(2023, 1, 1, 12, 25)
            potential_25min = calculate_potential_timestamps(start_25min, end_25min)
            @test potential_25min == 2

            # Same timestamp = 0 intervals
            potential_same = calculate_potential_timestamps(start_time, start_time)
            @test potential_same == 0

            # End before start = 0 intervals
            potential_negative = calculate_potential_timestamps(end_time, start_time)
            @test potential_negative == 0
        end
    end

    @testset "Integration Tests" begin
        
        @testset "test_complete_coverage_analysis" begin
            # Create realistic test data
            target_sensors = [
                SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s"),
                SensorColumn(sensorType="WindSpeed", statType="avg", height=160.0, columnName=:WS_160m, sensorDirection="N", unit="m/s")
            ]

            source_sensors = [
                SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s"),
                SensorColumn(sensorType="WindSpeed", statType="avg", height=140.0, columnName=:WS_140m, sensorDirection="N", unit="m/s")
            ]

            # Create 30 days of 10-minute data with 80% availability
            timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:4319]  # 30 days worth
            Random.seed!(123)  # For reproducible random data
            target_data = [i % 5 == 0 ? missing : 12.0 + randn() for i in 1:length(timestamps)]  # 80% available
            source_data = [i % 4 == 0 ? missing : 11.5 + randn() for i in 1:length(timestamps)]  # 75% available

            target_df = DataFrame(
                timestamp=timestamps, 
                WS_160m=target_data, 
                WS_120m=target_data .+ randn(length(timestamps))
            )
            source_df = DataFrame(
                timestamp=timestamps, 
                WS_140m=source_data, 
                WS_100m=source_data .+ randn(length(timestamps))
            )

            target_ts = TimeSeriesData(target_df, target_sensors)
            source_ts = TimeSeriesData(source_df, source_sensors)

            coverage = analyze_mast_pair_coverage(target_ts, source_ts)

            # Should return valid coverage result (not nothing)
            @test !isnothing(coverage)
            # Should use highest sensors (160m and 140m)
            @test coverage.overlap_days ≈ 18.0 atol=5.0  # ~60% of 30 days due to missing data
            @test coverage.concurrent_records > 0
            @test coverage.coverage_percentage > 50.0
            @test coverage.overlap_start == DateTime(2023,1,1)
        end

        @testset "test_precise_overlap_calculation" begin
            # Target: 1000 valid timestamps (days 1-25)
            target_timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:999]
            # Source: 800 valid timestamps (days 10-30) 
            source_timestamps = [DateTime(2023,1,5) + Minute(10*i) for i in 0:799]

            # Expected overlap: days 10-25 = ~600 timestamps
            # Expected days: (600 * 10) / (60 * 24) ≈ 4.17 days

            target_df = DataFrame(timestamp=target_timestamps, WS_120m=fill(12.0, 1000))
            source_df = DataFrame(timestamp=source_timestamps, WS_100m=fill(11.0, 800))

            target_ts = TimeSeriesData(target_df, [SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")])
            source_ts = TimeSeriesData(source_df, [SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")])

            coverage = analyze_mast_pair_coverage(target_ts, source_ts)

            @test !isnothing(coverage)  # Should return valid result for overlapping timestamps
            expected_overlap_records = length(intersect(Set(target_timestamps), Set(source_timestamps)))
            expected_days = (expected_overlap_records * 10.0) / (60.0 * 24.0)

            @test coverage.concurrent_records == expected_overlap_records
            @test coverage.overlap_days ≈ expected_days atol=0.01
        end
    end

    @testset "Edge Case Tests" begin
        
        @testset "test_nothing_return_scenarios" begin
            # Scenario 1: No wind speed sensors in target
            target_no_ws = [SensorColumn(sensorType="WindDirection", statType="avg", height=120.0, columnName=:WD_120m, sensorDirection="N", unit="deg")]
            source_with_ws = [SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection = "N", unit = "m/s")]
            
            target_df = DataFrame(timestamp=[DateTime(2023,1,1)], WD_120m=[180.0])
            source_df = DataFrame(timestamp=[DateTime(2023,1,1)], WS_120m=[12.0])
            
            target_ts = TimeSeriesData(target_df, target_no_ws)
            source_ts = TimeSeriesData(source_df, source_with_ws)
            
            @test isnothing(analyze_mast_pair_coverage(target_ts, source_ts))
            
            # Scenario 2: No wind speed sensors in source
            @test isnothing(analyze_mast_pair_coverage(source_ts, target_ts))
            
            # Scenario 3: No timestamp overlap
            target_jan = TimeSeriesData(
                DataFrame(timestamp=[DateTime(2023,1,1)], WS_120m=[12.0]),
                [SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")]
            )
            source_feb = TimeSeriesData(
                DataFrame(timestamp=[DateTime(2023,2,1)], WS_100m=[11.0]),
                [SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")]
            )
            
            @test isnothing(analyze_mast_pair_coverage(target_jan, source_feb))
        end

        @testset "test_no_wind_speed_sensors" begin
            # Target has wind speed, source doesn't
            target_sensors = [SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")]
            source_sensors = [SensorColumn(sensorType="WindDirection", statType="avg", height=120.0, columnName=:WD_120m, sensorDirection="N", unit="deg")]

            target_df = DataFrame(timestamp=[DateTime(2023,1,1)], WS_120m=[12.0])
            source_df = DataFrame(timestamp=[DateTime(2023,1,1)], WD_120m=[180.0])

            target_ts = TimeSeriesData(target_df, target_sensors)
            source_ts = TimeSeriesData(source_df, source_sensors)

            coverage = analyze_mast_pair_coverage(target_ts, source_ts)

            @test isnothing(coverage)  # Should return nothing when no wind speed sensors in source

            # Neither mast has wind speed sensors
            target_no_ws = [SensorColumn(sensorType="WindDirection", statType="avg", height=120.0, columnName=:WD_120m, sensorDirection="N", unit="deg")]
            source_no_ws = [SensorColumn(sensorType="Temperature", statType="avg", height=10.0, columnName=:Temp, sensorDirection="", unit="°C")]

            target_ts_no_ws = TimeSeriesData(DataFrame(timestamp=[DateTime(2023,1,1)], WD_120m=[180.0]), target_no_ws)
            source_ts_no_ws = TimeSeriesData(DataFrame(timestamp=[DateTime(2023,1,1)], Temp=[15.0]), source_no_ws)

            coverage_no_ws = analyze_mast_pair_coverage(target_ts_no_ws, source_ts_no_ws)
            @test isnothing(coverage_no_ws)  # Should return nothing when neither mast has wind speed sensors
        end

        @testset "test_no_valid_data_for_highest_sensors" begin
            # Both masts have highest sensors but all data is missing
            target_sensors = [SensorColumn(sensorType="WindSpeed", statType="avg", height=160.0, columnName=:WS_160m, sensorDirection="N", unit="m/s")]
            source_sensors = [SensorColumn(sensorType="WindSpeed", statType="avg", height=140.0, columnName=:WS_140m, sensorDirection="N", unit="m/s")]

            target_df = DataFrame(timestamp=[DateTime(2023,1,1), DateTime(2023,1,1,0,10)], WS_160m=[missing, missing])
            source_df = DataFrame(timestamp=[DateTime(2023,1,1), DateTime(2023,1,1,0,10)], WS_140m=[missing, missing])

            target_ts = TimeSeriesData(target_df, target_sensors)
            source_ts = TimeSeriesData(source_df, source_sensors)

            coverage = analyze_mast_pair_coverage(target_ts, source_ts)

            # Should return nothing when no valid data exists
            @test isnothing(coverage)
        end

        @testset "test_no_timestamp_overlap" begin
            # Target: January data, Source: February data (no overlap)
            target_timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:100]
            source_timestamps = [DateTime(2023,2,1) + Minute(10*i) for i in 0:100]

            target_df = DataFrame(timestamp=target_timestamps, WS_120m=fill(12.0, 101))
            source_df = DataFrame(timestamp=source_timestamps, WS_100m=fill(11.0, 101))

            target_ts = TimeSeriesData(target_df, [SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")])
            source_ts = TimeSeriesData(source_df, [SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")])

            coverage = analyze_mast_pair_coverage(target_ts, source_ts)

            @test isnothing(coverage)  # Should return nothing when no timestamp overlap exists
        end

        @testset "test_single_timestamp_overlap" begin
            # Only one common timestamp between masts
            common_time = DateTime(2023,1,15,12,0)
            target_timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:100] ∪ [common_time]
            source_timestamps = [DateTime(2023,2,1) + Minute(10*i) for i in 0:100] ∪ [common_time]

            target_df = DataFrame(timestamp=target_timestamps, WS_120m=fill(12.0, length(target_timestamps)))
            source_df = DataFrame(timestamp=source_timestamps, WS_100m=fill(11.0, length(source_timestamps)))

            target_ts = TimeSeriesData(target_df, [SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")])
            source_ts = TimeSeriesData(source_df, [SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")])

            coverage = analyze_mast_pair_coverage(target_ts, source_ts)

            @test !isnothing(coverage)  # Should return valid result for single timestamp overlap
            @test coverage.concurrent_records == 1
            expected_days_1_interval = (1 * 10.0) / (60.0 * 24.0)
            @test coverage.overlap_days ≈ expected_days_1_interval atol=0.000001
            @test coverage.overlap_start == common_time
            @test coverage.overlap_end == common_time
        end
    end

    @testset "@with_kw Constructor Tests" begin
        
        @testset "test_mast_pair_coverage_with_kw_construction" begin
            # Test keyword constructor
            coverage = MastPairCoverage(
                overlap_start = DateTime(2023, 1, 1),
                overlap_end = DateTime(2023, 6, 30),
                overlap_days = 180.5,
                concurrent_records = 26000,
                coverage_percentage = 89.5
            )

            @test coverage.overlap_start == DateTime(2023, 1, 1)
            @test coverage.overlap_end == DateTime(2023, 6, 30)
            @test coverage.overlap_days ≈ 180.5
            @test coverage.concurrent_records == 26000
            @test coverage.coverage_percentage ≈ 89.5

            # Test from_dict/to_dict still work with @with_kw
            coverage_dict = to_dict(coverage)
            @test haskey(coverage_dict, "overlap_start")
            @test haskey(coverage_dict, "overlap_days")

            recreated_coverage = from_dict(MastPairCoverage, coverage_dict)
            @test recreated_coverage.overlap_days ≈ coverage.overlap_days
            @test recreated_coverage.concurrent_records == coverage.concurrent_records
        end
    end

    @testset "Performance Tests" begin
        
        @testset "test_large_dataset_performance" begin
            # Full year of 10-minute data = 52,560 intervals
            year_timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:52559]

            # Create realistic missing data patterns (70% availability)
            Random.seed!(456)  # For reproducible performance testing
            target_data = [i % 10 < 7 ? 12.0 + randn() : missing for i in 1:length(year_timestamps)]
            source_data = [i % 10 < 7 ? 11.5 + randn() : missing for i in 1:length(year_timestamps)]

            target_df = DataFrame(timestamp=year_timestamps, WS_160m=target_data)
            source_df = DataFrame(timestamp=year_timestamps, WS_140m=source_data)

            target_ts = TimeSeriesData(target_df, [SensorColumn(sensorType="WindSpeed", statType="avg", height=160.0, columnName=:WS_160m, sensorDirection="N", unit="m/s")])
            source_ts = TimeSeriesData(source_df, [SensorColumn(sensorType="WindSpeed", statType="avg", height=140.0, columnName=:WS_140m, sensorDirection="N", unit="m/s")])

            # Performance test
            @time coverage = analyze_mast_pair_coverage(target_ts, source_ts)

            # Should complete in reasonable time (<5 seconds) and produce sensible results
            @test !isnothing(coverage)  # Should return valid result for year-long data
            @test coverage.overlap_days > 250.0  # Should be ~250-300 days with 70% availability
            @test coverage.overlap_days < 400.0  # Shouldn't exceed reasonable bounds
            @test coverage.concurrent_records > 20000  # Should have substantial overlap
        end

        @testset "test_memory_usage_efficiency" begin
            # Test with large dataset and monitor memory
            initial_memory = Base.gc_live_bytes()

            # Create large dataset
            large_timestamps = [DateTime(2023,1,1) + Minute(10*i) for i in 0:100000]  # ~19 months
            target_data = [i % 3 == 0 ? missing : 12.0 for i in 1:length(large_timestamps)]
            source_data = [i % 4 == 0 ? missing : 11.0 for i in 1:length(large_timestamps)]

            target_df = DataFrame(timestamp=large_timestamps, WS_120m=target_data)
            source_df = DataFrame(timestamp=large_timestamps, WS_100m=source_data)

            target_ts = TimeSeriesData(target_df, [SensorColumn(sensorType="WindSpeed", statType="avg", height=120.0, columnName=:WS_120m, sensorDirection="N", unit="m/s")])
            source_ts = TimeSeriesData(source_df, [SensorColumn(sensorType="WindSpeed", statType="avg", height=100.0, columnName=:WS_100m, sensorDirection="N", unit="m/s")])

            coverage = analyze_mast_pair_coverage(target_ts, source_ts)

            @test !isnothing(coverage)  # Should return valid result for large dataset

            final_memory = Base.gc_live_bytes()
            memory_increase = final_memory - initial_memory

            # Memory increase should be reasonable (< 100MB for this test)
            @test memory_increase < 100_000_000  # 100MB threshold
        end
    end
end

# Test Data Creation Helpers
"""
    create_test_timeseries(start_date, num_intervals, missing_rate=0.0, sensor_height=120.0)

Helper to create realistic test TimeSeriesData with controlled missing patterns.
"""
function create_test_timeseries(start_date::DateTime, num_intervals::Int, missing_rate::Float64=0.0, sensor_height::Float64=120.0)
    timestamps = [start_date + Minute(10*i) for i in 0:num_intervals-1]
    
    # Create data with specified missing rate
    Random.seed!(789)
    data = [rand() < missing_rate ? missing : 12.0 + randn() for _ in 1:num_intervals]
    
    column_name = Symbol("WS_$(Int(sensor_height))m")
    df = DataFrame(:timestamp=>timestamps, column_name=>data)
    sensors = [SensorColumn(sensorType="WindSpeed", statType="avg", height=sensor_height, columnName=column_name, sensorDirection="N", unit="m/s")]
    
    return TimeSeriesData(df, sensors)
end

"""
    create_overlap_scenario(target_days, source_days, overlap_days, missing_rate=0.1)

Helper to create specific overlap scenarios for testing.
"""
function create_overlap_scenario(target_days::Int, source_days::Int, overlap_days::Int, missing_rate::Float64=0.1)
    # Target starts at day 1
    target_start = DateTime(2023, 1, 1)
    target_intervals = target_days * 144  # 144 intervals per day
    target_ts = create_test_timeseries(target_start, target_intervals, missing_rate, 120.0)
    
    # Source starts to create desired overlap
    source_start = target_start + Day(target_days - overlap_days)
    source_intervals = source_days * 144
    source_ts = create_test_timeseries(source_start, source_intervals, missing_rate, 100.0)
    
    return target_ts, source_ts
end

# Validation Helpers
"""
    validate_day_calculation(concurrent_records, expected_days, tolerance=0.01)

Validate day calculation from concurrent records matches expected value.
"""
function validate_day_calculation(concurrent_records::Int, expected_days::Float64, tolerance::Float64=0.01)
    calculated_days = (concurrent_records * 10.0) / (60.0 * 24.0)
    @test calculated_days ≈ expected_days atol=tolerance
end

@testset "Helper Function Tests" begin
    @testset "test_helper_functions" begin
        # Test create_test_timeseries
        ts = create_test_timeseries(DateTime(2023, 1, 1), 288, 0.0, 120.0)  # 2 days, no missing data
        @test nrow(ts.df) == 288
        @test ts.sensors[1].height == 120.0
        @test ts.sensors[1].columnName == :WS_120m
        
        # Test create_overlap_scenario
        target_ts, source_ts = create_overlap_scenario(10, 8, 5, 0.0)  # 10 days target, 8 days source, 5 days overlap
        coverage = analyze_mast_pair_coverage(target_ts, source_ts)
        @test !isnothing(coverage)
        @test coverage.overlap_days ≈ 5.0 atol=0.1
        
        # Test validate_day_calculation
        validate_day_calculation(144, 1.0)  # 144 intervals = 1 day
        validate_day_calculation(720, 5.0)  # 720 intervals = 5 days
    end
end 