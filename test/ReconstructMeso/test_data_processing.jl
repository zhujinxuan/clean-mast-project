module TestDataProcessing

using Test
using Dates
using DataFrames
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.ReconstructMeso: TrainingTimeRange
using ...ReconstructMeso.DataProcessing

@testset "DataProcessing" begin
    # Create test data
    timestamps = DateTime(2024,1,1):Hour(1):DateTime(2024,1,2)
    df = DataFrame(
        timestamp = timestamps,
        ws_80m = [5.0, 6.0, missing, 7.0, 8.0, 6.0, missing, 5.0, 
                  4.0, 7.0, missing, 8.0, 6.0, missing, 7.0, 5.0, 
                  6.0, 7.0, missing, 8.0, 5.0, 6.0, missing, 7.0],
        wd_80m = [180.0, 185.0, missing, 190.0, 195.0, 180.0, missing, 185.0,
                  190.0, 185.0, missing, 180.0, 185.0, missing, 190.0, 185.0,
                  180.0, 185.0, missing, 190.0, 185.0, 180.0, missing, 185.0]
    )
    
    sensors = [
        SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s"),
        SensorColumn(:wd_80m, "WindDirection", "N", 80.0, "avg", "deg")
    ]
    
    ts = TimeSeriesData(df, sensors)
    time_range = TrainingTimeRange(DateTime(2024,1,1,2), DateTime(2024,1,1,22))

    @testset "ensure_complete_timeseries" begin
        # Test 10-minute completion
        completed = ensure_complete_timeseries(ts, time_range, Minute(10))
        @test size(completed.df, 1) == 121  # 20 hours * 6 10-min intervals + 1
        @test completed.sensors == sensors
        @test all(diff(completed.df.timestamp) .== Minute(10))
        
        # Test hourly completion
        completed_hourly = ensure_complete_timeseries(ts, time_range, Hour(1))
        @test size(completed_hourly.df, 1) == 21  # 20 hours + 1
        @test all(diff(completed_hourly.df.timestamp) .== Hour(1))
    end

    @testset "prepare_timeseries" begin
        prepared = prepare_timeseries(ts, time_range, Minute(10))
        @test issorted(prepared.df.timestamp)
        @test first(prepared.df.timestamp) == DateTime(2024,1,1,2)
        @test last(prepared.df.timestamp) == DateTime(2024,1,1,22)
    end

    @testset "average_timeseries" begin
        # Test 15-day averaging
        averaged = average_timeseries(ts, time_range, 15)
        @test size(averaged.df, 1) == 1  # Should have one period for this short range
        @test !ismissing(averaged.df[1, :ws_80m])  # Should have valid average
        @test !ismissing(averaged.df[1, :wd_80m])
        
        # Test with high missing ratio
        df_missing = copy(df)
        df_missing.ws_80m .= missing
        ts_missing = TimeSeriesData(df_missing, sensors)
        averaged_missing = average_timeseries(ts_missing, time_range, 15)
        @test ismissing(averaged_missing.df[1, :ws_80m])  # Should be missing due to >30% missing data
    end

    @testset "find_nearest_height_sensor" begin
        sensors_multi = [
            SensorColumn(:ws_60m, "WindSpeed", "N", 60.0, "avg", "m/s"),
            SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s"),
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s")
        ]
        
        # Test exact match
        @test find_nearest_height_sensor(80.0, sensors_multi, "WindSpeed").height == 80.0
        
        # Test nearest match
        @test find_nearest_height_sensor(85.0, sensors_multi, "WindSpeed").height == 80.0
        @test find_nearest_height_sensor(95.0, sensors_multi, "WindSpeed").height == 100.0
        
        # Test no match
        @test isnothing(find_nearest_height_sensor(80.0, sensors_multi, "Temperature"))
    end

    @testset "calculate_training_timerange" begin
        # Add new test for the conversion function
        input_range = TimeRange(nothing, nothing)
        result = calculate_training_timerange(ts, input_range)
        @test result isa TrainingTimeRange
        @test result.min <= result.max
        @test result.max - result.min ≤ Year(1)

        # Test with specified min
        input_range = TimeRange(DateTime(2024,1,1), nothing)
        result = calculate_training_timerange(ts, input_range)
        @test result.min == DateTime(2024,1,1)
        @test result.max - result.min ≤ Year(1)

        # Test with specified max
        input_range = TimeRange(nothing, DateTime(2024,1,2))
        result = calculate_training_timerange(ts, input_range)
        @test result.max == DateTime(2024,1,2)
        @test result.max - result.min ≤ Year(1)

        # Test with both specified
        input_range = TimeRange(DateTime(2024,1,1), DateTime(2024,1,2))
        result = calculate_training_timerange(ts, input_range)
        @test result.min == DateTime(2024,1,1)
        @test result.max == DateTime(2024,1,2)
    end
end

end 