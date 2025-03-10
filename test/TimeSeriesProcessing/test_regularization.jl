module TestRegularization

using Test
using DataFrames
using Dates
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, SensorColumn, TimeRange
using CleanMastProject.TimeSeriesProcessing.Regularization: ensure_regular_intervals, find_gaps, validate_intervals

function runtests()
    @testset "Regularization" begin
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
        time_range = TimeRange(DateTime(2024,1,1,2), DateTime(2024,1,1,22))

        # Test ensure_regular_intervals
        regular_ts = ensure_regular_intervals(ts, time_range, Minute(10))
        @test size(regular_ts.df, 1) == 121  # 20 hours * 6 10-min intervals + 1
        @test all(diff(regular_ts.df.timestamp) .== Minute(10))
        @test regular_ts.sensors == sensors

        # Test timestamp alignment and missing values
        mask_timestamp = in.(regular_ts.df.timestamp, Ref(ts.df.timestamp))
        mask2_timestamp = in.(ts.df.timestamp, Ref(regular_ts.df.timestamp))
        
        # Test existing timestamps match original data
        for symbol in [:ws_80m, :wd_80m]
            @test all(
                isequal.(regular_ts.df[mask_timestamp, symbol], 
                         ts.df[mask2_timestamp, symbol])
            )
        end
        
        # Test inserted timestamps have missing sensor values
        @test all(
            all(ismissing, col) 
            for col in eachcol(
                regular_ts.df[.!mask_timestamp, [:ws_80m, :wd_80m]]
            )
        )
        
        # Test find_gaps
        original_gaps = find_gaps(ts, Hour(1))
        @test length(original_gaps) == 0
        regularized_gaps = find_gaps(regular_ts, Minute(10))
        @test length(regularized_gaps) == 0
        
        # Test validate_intervals
        @test validate_intervals(ts, Hour(1))  # Original data has gaps
        @test validate_intervals(regular_ts, Minute(10))  # Regularized data should be valid
    end
end

end 