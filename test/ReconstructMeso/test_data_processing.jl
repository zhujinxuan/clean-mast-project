module TestDataProcessing

using Test
using Dates
using DataFrames
using Statistics
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, SensorColumn
using CleanMastProject.Types.ReconstructMeso: TrainingTimeRange
using CleanMastProject.Types.CleanMastConfig: TimeRange
using CleanMastProject.ReconstructMeso.DataProcessing: ensure_complete_timeseries, 
    find_nearest_height_sensor, calculate_training_timerange, interpolate_meso_data,
    prepare_training_data

@testset "DataProcessing" begin
    # Create test data
    timestamps = collect(DateTime(2024,1,1):Hour(1):DateTime(2024,1,2))
    ws_data = [5.0, 6.0, missing, 7.0, 8.0, 6.0, missing, 5.0, 
              4.0, 7.0, missing, 8.0, 6.0, missing, 7.0, 5.0, 
              6.0, 7.0, missing, 8.0, 5.0, 6.0, missing, 7.0, 8.0]
    wd_data = [180.0, 185.0, missing, 190.0, 195.0, 180.0, missing, 185.0,
              190.0, 185.0, missing, 180.0, 185.0, missing, 190.0, 185.0,
              180.0, 185.0, missing, 190.0, 185.0, 180.0, missing, 185.0, 190.0]
    
    df = DataFrame(
        timestamp = timestamps,
        ws_80m = ws_data,
        wd_80m = wd_data
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

    @testset "interpolate_meso_data" begin
        # Create test data with hourly values
        meso_ts = TimeSeriesData(
            DataFrame(
                timestamp = collect(DateTime(2024,1,1,2):Hour(1):DateTime(2024,1,1,22)),
                ws_80m = collect(5.0:25.0),
                wd_80m = mod.(collect(170.0:10.0:390.0), 360.0)
            ),
            sensors
        )
        
        # Test interpolation to 10-minute intervals
        interpolated = interpolate_meso_data(meso_ts, time_range)
        
        # Check timestamps
        @test size(interpolated.df, 1) == 121  # 20 hours * 6 10-min intervals + 1
        @test all(diff(interpolated.df.timestamp) .== Minute(10))
        
        # Check wind speed interpolation (linear)
        @test interpolated.df[1, :ws_80m] ≈ 5.0  # First value
        @test interpolated.df[7, :ws_80m] ≈ 5.5  # Midpoint between 5.0 and 6.0
        
        # Check wind direction interpolation (circular)
        @test interpolated.df[1, :wd_80m] ≈ 170.0  # First value
        # Test circular interpolation across 360° boundary
        idx = findfirst(x -> x.wd_80m > 350.0, meso_ts.df)
        if !isnothing(idx)
            before_val = meso_ts.df[idx, :wd_80m]
            after_val = meso_ts.df[idx+1, :wd_80m]
            midpoint_idx = (idx-1)*6 + 4  # Index in interpolated data for midpoint
            expected = mod(before_val + (after_val - before_val + 180) % 360 - 180, 360) / 2
            @test isapprox(interpolated.df[midpoint_idx, :wd_80m], expected, atol=1.0)
        end
    end

    @testset "prepare_training_data" begin
        # Create test meso data with hourly values
        meso_ts = TimeSeriesData(
            DataFrame(
                timestamp = collect(DateTime(2024,1,1,2):Hour(1):DateTime(2024,1,1,22)),
                ws_80m = collect(5.0:25.0),
                wd_80m = mod.(collect(170.0:10.0:390.0), 360.0)
            ),
            sensors
        )
        
        # Test preparation of both datasets
        complete_mast, interpolated_meso = prepare_training_data(ts, meso_ts, time_range)
        
        # Check mast data
        @test size(complete_mast.df, 1) == 121
        @test all(diff(complete_mast.df.timestamp) .== Minute(10))
        
        # Check meso data
        @test size(interpolated_meso.df, 1) == 121
        @test all(diff(interpolated_meso.df.timestamp) .== Minute(10))
        
        # Check alignment of timestamps
        @test all(complete_mast.df.timestamp .== interpolated_meso.df.timestamp)
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
        # Test with no time range specified
        input_range = TimeRange(nothing, nothing)
        result = calculate_training_timerange(ts, input_range)
        @test result isa TrainingTimeRange
        @test result.min == DateTime(2023,1,1)
        @test result.max == DateTime(2024,1,1) - Second(1)

        # Test with specified min
        input_range = TimeRange(DateTime(2024,1,1), nothing)
        result = calculate_training_timerange(ts, input_range)
        @test result.min == DateTime(2024,1,1)
        @test result.max == DateTime(2025,1,1) - Second(1)

        # Test with specified max
        input_range = TimeRange(nothing, DateTime(2024,1,2))
        result = calculate_training_timerange(ts, input_range)
        @test result.max == DateTime(2024,1,2)
        @test result.min == DateTime(2023,1,1)

        # Test with both specified
        input_range = TimeRange(DateTime(2024,1,1), DateTime(2024,1,2))
        result = calculate_training_timerange(ts, input_range)
        @test result.min == DateTime(2024,1,1)
        @test result.max == DateTime(2024,1,2)
    end
end

end 