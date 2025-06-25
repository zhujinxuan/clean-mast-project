module TestTimeRangeProcessor

using Test
using DataFrames
using Dates
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, TimeRange
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.Types.CleanMastConfig: ConfigTimeRange
using CleanMastProject.TimeSeriesProcessing.TimeRangeProcessor: calculate_reconstruction_time_range

function runtests()
    @testset "TimeRangeProcessor" begin
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

        # Test calculate_time_range with no constraints
        config_range = nothing
        calculated = calculate_reconstruction_time_range(ts, config_range)
        @test calculated isa TimeRange
        @test calculated.max == Year(1) + calculated.min - Second(1)
        
        # Test with ConfigTimeRange constraints
        config_range = ConfigTimeRange(DateTime(2024,1,1), DateTime(2024,1,2))
        calculated = calculate_reconstruction_time_range(ts, config_range)
        @test calculated.min == DateTime(2024,1,1)
        @test calculated.max == DateTime(2024,1,2) - Second(1)  # Adjusted to avoid partial day
        
    end
end

end 