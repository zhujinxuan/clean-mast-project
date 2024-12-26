module TestReconstruction

using Test
using Dates
using DataFrames
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.CleanMastConfig: TimeRange
using ...Types.ReconstructMeso: WindSpeedTrainResult, WindDirectionTrainResult
using ...ReconstructMeso.Reconstruction

@testset "Reconstruction" begin
    # Create test data
    timestamps = DateTime(2024,1,1):Hour(1):DateTime(2024,1,2)
    
    # Mast data with missing values
    mast_df = DataFrame(
        timestamp = timestamps,
        ws_80m = [5.0, missing, 7.0, missing, 9.0, missing, 11.0, missing],
        wd_80m = [180.0, missing, 200.0, missing, 220.0, missing, 240.0, missing]
    )
    
    # Meso data (complete)
    meso_df = DataFrame(
        timestamp = timestamps,
        ws_75m = collect(2.0:2.0:16.0),
        wd_75m = collect(175.0:5.0:210.0)
    )
    
    mast_sensors = [
        SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s"),
        SensorColumn(:wd_80m, "WindDirection", "N", 80.0, "avg", "deg")
    ]
    
    meso_sensors = [
        SensorColumn(:ws_75m, "WindSpeed", "N", 75.0, "avg", "m/s"),
        SensorColumn(:wd_75m, "WindDirection", "N", 75.0, "avg", "deg")
    ]
    
    mast_ts = TimeSeriesData(mast_df, mast_sensors)
    meso_ts = TimeSeriesData(meso_df, meso_sensors)
    
    time_range = TimeRange(DateTime(2024,1,1), DateTime(2024,1,2))
    
    # Create training results
    ws_results = Dict(
        :ws_80m => WindSpeedTrainResult(
            mast_sensors[1],
            meso_sensors[1],
            2.0,  # slope
            1.0   # intercept
        )
    )
    
    wd_results = Dict(
        :wd_80m => WindDirectionTrainResult(
            mast_sensors[2],
            meso_sensors[2],
            5.0   # difference
        )
    )

    @testset "fill_missing_data" begin
        result = fill_missing_data(mast_ts, meso_ts, time_range, ws_results, wd_results)
        
        # Check wind speed reconstruction
        filled_ws = result.df[ismissing.(mast_df.ws_80m), :ws_80m]
        expected_ws = @. 2.0 * meso_df[ismissing.(mast_df.ws_80m), :ws_75m] + 1.0
        @test all(isapprox.(filled_ws, expected_ws, atol=0.1))
        
        # Check wind direction reconstruction
        filled_wd = result.df[ismissing.(mast_df.wd_80m), :wd_80m]
        expected_wd = @. mod(meso_df[ismissing.(mast_df.wd_80m), :wd_75m] + 5.0, 360)
        @test all(isapprox.(filled_wd, expected_wd, atol=0.1))
    end
end

end 