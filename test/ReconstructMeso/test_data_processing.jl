module TestDataProcessing

using Test
using DataFrames
using Dates
using CleanMastProject.Types.CleanMastConfig: TimeRange
using Statistics
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.SensorColumns: SensorColumn, find_nearest_height_sensor
using CleanMastProject.Types.ReconstructMeso: TrainingTimeRange, WindSpeedTrainResult, 
                                            WindDirectionTrainResult, WindSpeedSectorModel
using CleanMastProject.ReconstructMeso.DataProcessing: 
    calculate_training_timerange, interpolate_meso_data,
    ensure_complete_timeseries, prepare_training_data
using CleanMastProject.ReconstructMeso.Reconstruction:
    ensure_training_range, fill_missing_data

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
        SensorColumn(:ws_80m, "ws_80m", "WindSpeed", "N", 80.0, "avg", "m/s"),
        SensorColumn(:wd_80m, "wd_80m", "WindDirection", "N", 80.0, "avg", "deg")
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
        timestamps = collect(DateTime(2024,1,1,2):Hour(1):DateTime(2024,1,1,22))
        n_points = length(timestamps)
        # every hour, wind direction changes by 6 degrees
        meso_ts = TimeSeriesData(
            DataFrame(
                timestamp = timestamps,
                ws_80m = collect(range(5.0, 25.0, length=n_points)),
                wd_80m = mod.(collect(range(170.0, 390.0, length=n_points)), 360.0)
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
        @test interpolated.df[4, :ws_80m] ≈ 5.5  # Midpoint between 5.0 and 6.0
        
        # Check wind direction interpolation (circular)
        @test interpolated.df[1, :wd_80m] ≈ 170.0  # First value
        # Test circular interpolation across 360° boundary
        idx = findfirst(i -> meso_ts.df[i, :wd_80m] > 350.0, 1:nrow(meso_ts.df))
        if !isnothing(idx)
            before_val = meso_ts.df[idx, :wd_80m]
            after_val = meso_ts.df[idx+1, :wd_80m]
            midpoint_idx = (idx-1)*6 + 4  # Index in interpolated data for midpoint
            expected = mod((before_val + after_val+360)/2, 360)
            @test isapprox(interpolated.df[midpoint_idx, :wd_80m], expected, atol=1.0)
        end
    end

    @testset "prepare_training_data" begin
        # Create test data
        df = DataFrame(
            timestamp = [DateTime(2020,1,1), DateTime(2020,1,2)],
            speed_120m = [10.0, missing]
        )
        sensors = [SensorColumn(:speed_120m, "speed_{height}m", "WindSpeed", "N", 120.0, "avg", "m/s", originalColumnName=:speed_120m, multiplier=1.0)]
        ts = TimeSeriesData(df, sensors)
        
        meso_df = DataFrame(
            timestamp = [DateTime(2020,1,1), DateTime(2020,1,2) - Hour(1), DateTime(2020,1,2)],
            speed_100m = [12.0, 13.0 , 11.0]
        )
        sensors = [SensorColumn(:speed_100m, "speed_{height}m", "WindSpeed", "N", 100.0, "avg", "m/s", originalColumnName=:speed_100m, multiplier=1.0)]
        meso_ts = TimeSeriesData(meso_df, sensors)
        
        # Test data preparation
        complete_mast, interpolated_meso = prepare_training_data(ts, meso_ts)
        
        # Check results
        @test nrow(complete_mast.df) == 145
        @test nrow(interpolated_meso.df) == 145
        @test complete_mast.df[2, :speed_120m] === missing
        @test interpolated_meso.df[145, :speed_100m] == 11.0
    end

    @testset "find_nearest_height_sensor" begin
        sensors_multi = [
            SensorColumn(:ws_60m, "ws_60m", "WindSpeed", "N", 60.0, "avg", "m/s"),
            SensorColumn(:ws_80m, "ws_80m", "WindSpeed", "N", 80.0, "avg", "m/s"),
            SensorColumn(:ws_100m, "ws_100m", "WindSpeed", "N", 100.0, "avg", "m/s")
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
        @test result.min == DateTime(2019,1,1)
        @test result.max == DateTime(2020,1,1) - Second(1)

        # Test with specified min
        input_range = TimeRange(DateTime(2024,1,1), nothing)
        result = calculate_training_timerange(ts, input_range)
        @test result.min == DateTime(2024,1,1)
        @test result.max == DateTime(2025,1,1) - Second(1)

        # Test with specified max
        input_range = TimeRange(nothing, DateTime(2024,1,2))
        result = calculate_training_timerange(ts, input_range)
        @test result.max == DateTime(2024,1,2) - Second(1)
        @test result.min == DateTime(2023,1,1)

        # Test with both specified
        input_range = TimeRange(DateTime(2024,1,1), DateTime(2024,1,2))
        result = calculate_training_timerange(ts, input_range)
        @test result.min == DateTime(2024,1,1)
        @test result.max == DateTime(2024,1,2) - Second(1)
    end

    @testset "interpolate_meso_data with specific pattern" begin
        # Create functions for the true wind patterns
        function true_wind_speed(t::DateTime)::Float64
            h = hour(t) + minute(t)/60
            if h <= 6
                return 5.0 + (8.0 - 5.0) * h / 6  # Linear increase from 5 to 8
            elseif h <= 18
                return 8.0  # Constant at 8
            else
                return 8.0 - (8.0 - 5.0) * (h - 18) / 6  # Linear decrease from 8 to 5
            end
        end

        function true_wind_direction(t::DateTime)::Float64
            h = hour(t) + minute(t)/60
            if h <= 6
                return 30.0 + (210.0 - 30.0) * h / 6  # Linear increase from 30 to 210
            elseif h <= 18
                return 210.0  # Constant at 210
            else
                # Handle circular interpolation for direction
                return mod(210.0 + (30.0 + 360.0 - 210.0) * (h - 18) / 6, 360.0)
            end
        end

        # Create hourly data
        timestamps = collect(DateTime(2024,1,1):Hour(1):(DateTime(2024,1,2)))
        df = DataFrame(
            timestamp = timestamps,
            ws_80m = map(true_wind_speed, timestamps),
            wd_80m = map(true_wind_direction, timestamps)
        )

        sensors = [
            SensorColumn(:ws_80m, "ws_80m", "WindSpeed", "N", 80.0, "avg", "m/s"),
            SensorColumn(:wd_80m, "wd_80m", "WindDirection", "N", 80.0, "avg", "deg")
        ]

        ts = TimeSeriesData(df, sensors)
        time_range = TrainingTimeRange(DateTime(2024,1,1), DateTime(2024,1,2) - Second(1))

        # Interpolate to 10-minute intervals
        interpolated = interpolate_meso_data(ts, time_range)

        # Check timestamps
        @test size(interpolated.df, 1) == 24 * 6  # 24 hours * 6 10-min intervals
        @test all(diff(interpolated.df.timestamp) .== Minute(10))

        # Check interpolated values against true functions
        for df_timestamp in DateTime(2024,1,1):Minute(10):DateTime(2024,1,1,23) 
            idx = findfirst(timestamp -> timestamp == df_timestamp, interpolated.df.timestamp)
            @test isapprox(interpolated.df[idx, :ws_80m], true_wind_speed(df_timestamp), atol=0.1)
            dir_diff = abs(mod(interpolated.df[idx, :wd_80m] - true_wind_direction(df_timestamp) + 180, 360) - 180)
            @test dir_diff < 1.0
        end
    end

    @testset "ensure_training_range" begin
        # Create test data with gaps
        df = DataFrame(
            timestamp = [DateTime(2020,1,1), DateTime(2020,1,2)],
            ws_80m = [10.0, 11.0],
            wd_80m = [180.0, 185.0]
        )
        
        # Create time range that extends beyond data
        time_range = TrainingTimeRange(
            DateTime(2019,12,31),
            DateTime(2020,1,3)
        )
        
        # Test range extension
        result_df = ensure_training_range(df, time_range)
        
        # Check results
        @test result_df !== df  # Should be a new DataFrame
        @test nrow(result_df) > nrow(df)  # Should have added rows
        @test minimum(result_df.timestamp) == time_range.min
        @test maximum(result_df.timestamp) == time_range.max
        @test all(diff(result_df.timestamp) .== Minute(10))  # Should have 10-minute intervals
        
        # Check original data is preserved
        for row in eachrow(df)
            result_row = result_df[result_df.timestamp .== row.timestamp, :]
            @test !isempty(result_row)
            @test result_row.ws_80m[1] == row.ws_80m
            @test result_row.wd_80m[1] == row.wd_80m
        end
        
        # Check new timestamps have missing values
        new_timestamps = setdiff(result_df.timestamp, df.timestamp)
        for ts in new_timestamps
            result_row = result_df[result_df.timestamp .== ts, :]
            @test ismissing(result_row.ws_80m[1])
            @test ismissing(result_row.wd_80m[1])
        end
    end

end

end 