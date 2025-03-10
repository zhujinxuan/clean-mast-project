module TestInterpolation

using Test
using DataFrames
using Dates
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, SensorColumn, TimeRange
using CleanMastProject.TimeSeriesProcessing.Interpolation: interpolate_timeseries, interpolate_to_interval

function runtests()
    @testset "Interpolation" begin
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

        # Test interpolation to specific timestamps
        target_timestamps = collect(DateTime(2024,1,1,2):Minute(30):DateTime(2024,1,1,4))
        interpolated = interpolate_timeseries(ts, target_timestamps)
        
        @test size(interpolated.df, 1) == length(target_timestamps)
        @test all(interpolated.df.timestamp .== target_timestamps)
        @test interpolated.sensors == sensors
        
        # Test interpolate_to_interval
        hourly = interpolate_to_interval(ts, Hour(1))
        @test all(diff(hourly.df.timestamp) .== Hour(1))
        
        # Test wind direction circular interpolation
        wd_test_df = DataFrame(
            timestamp = [DateTime(2024,1,1), DateTime(2024,1,1,1)],
            wd_test = [350.0, 10.0]
        )
        wd_test_sensors = [
            SensorColumn(:wd_test, "WindDirection", "N", 80.0, "avg", "deg")
        ]
        wd_test_ts = TimeSeriesData(wd_test_df, wd_test_sensors)
        
        mid_timestamps = [DateTime(2024,1,1) + Minute(30)]
        interpolated_wd = interpolate_timeseries(wd_test_ts, mid_timestamps)
        # Should interpolate through the shorter arc (350° -> 0° -> 10°)
        @test isapprox(interpolated_wd.df[1, :wd_test], 0.0, atol=1.0)

        @testset "Complex Interpolation Patterns" begin
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

            ts = TimeSeriesData(df, sensors)
            
            # Test interpolation to 10-minute intervals
            target_timestamps = collect(DateTime(2024,1,1):Minute(10):DateTime(2024,1,1,23,50))
            interpolated = interpolate_timeseries(ts, target_timestamps)

            # Check interpolated values against true functions
            for df_timestamp in target_timestamps
                idx = findfirst(timestamp -> timestamp == df_timestamp, interpolated.df.timestamp)
                @test isapprox(interpolated.df[idx, :ws_80m], true_wind_speed(df_timestamp), atol=0.1)
                dir_diff = abs(mod(interpolated.df[idx, :wd_80m] - true_wind_direction(df_timestamp) + 180, 360) - 180)
                @test dir_diff < 1.0
            end
        end
    end
end

end 