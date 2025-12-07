"""
Tests for IntervalDetection module

This test suite covers various scenarios for detecting representative intervals
in time series data, including regular intervals, irregular data, and edge cases.
"""

using Test
using Dates
using DataFrames
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.TimeSeriesProcessing.IntervalDetection: detect_representative_interval, calculate_expected_points, get_interval_statistics

@testset "IntervalDetection Tests" begin
    
    @testset "Regular 10-minute intervals" begin
        # Create test data with perfect 10-minute intervals
        start_time = DateTime(2023, 1, 1, 0, 0, 0)
        timestamps = [start_time + Minute(10 * i) for i in 0:143]  # 24 hours of 10-min data
        
        df = DataFrame(
            timestamp = timestamps,
            sensor1 = rand(length(timestamps))
        )
        
        sensors = [SensorColumn(columnName=:sensor1, sensorType="WindSpeed", statType="avg", height=50.0, unit="m/s", sensorDirection="N")]
        ts_data = TimeSeriesData(df, sensors)
        
        interval = detect_representative_interval(ts_data)
        @test interval == Minute(10)
        
        expected_points = calculate_expected_points(ts_data, interval)
        @test expected_points == 144  # 24 hours * 6 points per hour + 1
    end
    
    @testset "Regular 1-hour intervals" begin
        # Create test data with 1-hour intervals
        start_time = DateTime(2023, 1, 1, 0, 0, 0)
        timestamps = [start_time + Hour(i) for i in 0:23]  # 24 hours of hourly data
        
        df = DataFrame(
            timestamp = timestamps,
            sensor1 = rand(length(timestamps))
        )
        
        sensors = [SensorColumn(columnName=:sensor1, sensorType="WindSpeed", statType="avg", height=50.0, unit="m/s", sensorDirection="N")]
        ts_data = TimeSeriesData(df, sensors)

        interval = detect_representative_interval(ts_data)
        @test interval == Minute(60)

        expected_points = calculate_expected_points(ts_data, interval)
        @test expected_points == 24
    end

    @testset "Mixed intervals with 10-minute majority" begin
        # Create data where 10-minute is most common, but some 20-minute gaps exist
        start_time = DateTime(2023, 1, 1, 0, 0, 0)
        timestamps = DateTime[]

        # Add mostly 10-minute intervals
        current_time = start_time
        for i in 1:100
            push!(timestamps, current_time)
            if i % 10 == 0  # Every 10th point, make a 20-minute gap
                current_time += Minute(20)
            else
                current_time += Minute(10)
            end
        end

        df = DataFrame(
            timestamp = timestamps,
            sensor1 = rand(length(timestamps))
        )

        sensors = [SensorColumn(columnName=:sensor1, sensorType="WindSpeed", statType="avg", height=50.0, unit="m/s", sensorDirection="N")]
        ts_data = TimeSeriesData(df, sensors)
        
        interval = detect_representative_interval(ts_data)
        @test interval == Minute(10)  # Should detect 10-minute as most common
    end
    
    @testset "Edge case: Single timestamp" begin
        # Test with only one timestamp
        df = DataFrame(
            timestamp = [DateTime(2023, 1, 1, 0, 0, 0)],
            sensor1 = [1.0]
        )
        
        sensors = [SensorColumn(columnName=:sensor1, sensorType="WindSpeed", statType="avg", height=50.0, unit="m/s", sensorDirection="N")]
        ts_data = TimeSeriesData(df, sensors)

        interval = detect_representative_interval(ts_data)
        @test interval == Minute(10)  # Should return default

        expected_points = calculate_expected_points(ts_data, interval)
        @test expected_points == 0
    end

    @testset "Edge case: No timestamps" begin
        # Test with empty data
        df = DataFrame(
            timestamp = DateTime[],
            sensor1 = Float64[]
        )

        sensors = [SensorColumn(columnName=:sensor1, sensorType="WindSpeed", statType="avg", height=50.0, unit="m/s", sensorDirection="N")]
        ts_data = TimeSeriesData(df, sensors)
        
        interval = detect_representative_interval(ts_data)
        @test interval == Minute(10)  # Should return default
        
        expected_points = calculate_expected_points(ts_data, interval)
        @test expected_points == 0
    end
    
    @testset "Edge case: Missing timestamps" begin
        # Test with missing timestamps
        df = DataFrame(
            timestamp = [DateTime(2023, 1, 1, 0, 0, 0), missing, DateTime(2023, 1, 1, 0, 10, 0)],
            sensor1 = [1.0, 2.0, 3.0]
        )
        
        sensors = [SensorColumn(columnName=:sensor1, sensorType="WindSpeed", statType="avg", height=50.0, unit="m/s", sensorDirection="N")]
        ts_data = TimeSeriesData(df, sensors)

        interval = detect_representative_interval(ts_data)
        @test interval == Minute(10)
    end

    @testset "Irregular intervals" begin
        # Test with completely irregular intervals
        timestamps = [
            DateTime(2023, 1, 1, 0, 0, 0),
            DateTime(2023, 1, 1, 0, 7, 0),   # 7 minutes
            DateTime(2023, 1, 1, 0, 15, 0),  # 8 minutes
            DateTime(2023, 1, 1, 0, 22, 0),  # 7 minutes
            DateTime(2023, 1, 1, 0, 30, 0),  # 8 minutes
            DateTime(2023, 1, 1, 0, 37, 0),  # 7 minutes
        ]

        df = DataFrame(
            timestamp = timestamps,
            sensor1 = rand(length(timestamps))
        )

        sensors = [SensorColumn(columnName=:sensor1, sensorType="WindSpeed", statType="avg", height=50.0, unit="m/s", sensorDirection="N")]
        ts_data = TimeSeriesData(df, sensors)
        
        interval = detect_representative_interval(ts_data)
        @test interval == Minute(7)  # 7 minutes is most common
    end
    
    @testset "get_interval_statistics function" begin
        # Test the statistics function
        start_time = DateTime(2023, 1, 1, 0, 0, 0)
        timestamps = [start_time + Minute(10 * i) for i in 0:10]
        
        df = DataFrame(
            timestamp = timestamps,
            sensor1 = rand(length(timestamps))
        )
        
        sensors = [SensorColumn(columnName=:sensor1, sensorType="WindSpeed", statType="avg", height=50.0, unit="m/s", sensorDirection="N")]
        ts_data = TimeSeriesData(df, sensors)

        stats = get_interval_statistics(ts_data)

        @test stats.representative_interval == Minute(10)
        @test stats.total_points == 11
        @test stats.expected_points > 0
        @test haskey(stats.interval_distribution, 10)
        @test stats.interval_distribution[10] == 10  # 10 intervals of 10 minutes each
    end

    @testset "Tie-breaking: Choose smallest interval" begin
        # Create data where two intervals have equal frequency
        timestamps = [
            DateTime(2023, 1, 1, 0, 0, 0),
            DateTime(2023, 1, 1, 0, 10, 0),  # 10 min
            DateTime(2023, 1, 1, 0, 20, 0),  # 10 min
            DateTime(2023, 1, 1, 0, 35, 0),  # 15 min
            DateTime(2023, 1, 1, 0, 50, 0),  # 15 min
        ]

        df = DataFrame(
            timestamp = timestamps,
            sensor1 = rand(length(timestamps))
        )

        sensors = [SensorColumn(columnName=:sensor1, sensorType="WindSpeed", statType="avg", height=50.0, unit="m/s", sensorDirection="N")]
        ts_data = TimeSeriesData(df, sensors)
        
        interval = detect_representative_interval(ts_data)
        @test interval == Minute(10)  # Should choose smaller interval in case of tie
    end
    
end
