module TestReconstruction

using Test
using Dates
using DataFrames
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, SensorColumn
using CleanMastProject.Types.ReconstructMeso: TrainingTimeRange, WindSpeedTrainResult, WindDirectionTrainResult
using CleanMastProject.ReconstructMeso.Reconstruction: calculate_interpolated_value, fill_missing_data, interpolate_meso_values

@testset "Reconstruction" begin
    # Create test data
    timestamps = collect(DateTime(2024,1,1):Hour(1):DateTime(2024,1,2))
    
    # Mast data with missing values
    mast_df = DataFrame(
        timestamp = timestamps[1:8],
        ws_80m = [5.0, missing, 7.0, missing, 9.0, missing, 11.0, missing],
        wd_80m = [180.0, missing, 200.0, missing, 220.0, missing, 240.0, missing]
    )
    
    # Meso data (complete)
    meso_df = DataFrame(
        timestamp = timestamps[1:8],
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
    
    time_range = TrainingTimeRange(DateTime(2024,1,1), DateTime(2024,1,2))
    
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

    @testset "calculate_interpolated_value" begin
        # Test linear interpolation
        @test calculate_interpolated_value(0.0, 10.0, 0.5, false) ≈ 5.0
        @test calculate_interpolated_value(0.0, 10.0, 0.0, false) ≈ 0.0
        @test calculate_interpolated_value(0.0, 10.0, 1.0, false) ≈ 10.0
        
        # Test circular interpolation (wind direction)
        # Normal case
        @test calculate_interpolated_value(350.0, 10.0, 0.5, true) ≈ 0.0
        # Small angle difference
        @test calculate_interpolated_value(180.0, 190.0, 0.5, true) ≈ 185.0
        # Crossing 0/360 boundary
        @test calculate_interpolated_value(350.0, 10.0, 0.25, true) ≈ 355.0
        # Large angle difference
        @test calculate_interpolated_value(10.0, 350.0, 0.5, true) ≈ 0.0
    end

    @testset "interpolate_meso_values" begin
        # Create test data
        df = DataFrame(
            timestamp = [
                DateTime(2023, 1, 1, 0),
                DateTime(2023, 1, 1, 1),
                DateTime(2023, 1, 1, 2),
                DateTime(2023, 1, 1, 3),
                DateTime(2023, 1, 1, 4)
            ],
            ws = [10.0, missing, 20.0, missing, 15.0],
            wd = [350.0, missing, 10.0, missing, 30.0]
        )
        meso_ts = TimeSeriesData(df, [])
        
        # Test wind speed (linear) interpolation
        hours_to_test = [
            DateTime(2023, 1, 1, 0),  # Exact match
            DateTime(2023, 1, 1, 1),  # Need interpolation
            DateTime(2023, 1, 1, 2),  # Exact match
            DateTime(2023, 1, 1, 3),  # Need interpolation
            DateTime(2023, 1, 1, 4)   # Exact match
        ]
        
        ws_results = interpolate_meso_values(meso_ts, hours_to_test, :ws)
        @test ws_results[DateTime(2023, 1, 1, 0)] ≈ 10.0
        @test ws_results[DateTime(2023, 1, 1, 1)] ≈ 15.0
        @test ws_results[DateTime(2023, 1, 1, 2)] ≈ 20.0
        @test ws_results[DateTime(2023, 1, 1, 3)] ≈ 17.5
        @test ws_results[DateTime(2023, 1, 1, 4)] ≈ 15.0
        
        # Test wind direction (circular) interpolation
        wd_results = interpolate_meso_values(meso_ts, hours_to_test, :wd, is_circular=true)
        @test wd_results[DateTime(2023, 1, 1, 0)] ≈ 350.0
        @test wd_results[DateTime(2023, 1, 1, 1)] ≈ 0.0
        @test wd_results[DateTime(2023, 1, 1, 2)] ≈ 10.0
        @test wd_results[DateTime(2023, 1, 1, 3)] ≈ 20.0
        @test wd_results[DateTime(2023, 1, 1, 4)] ≈ 30.0
        
        # Test with missing values
        df_missing = DataFrame(
            timestamp = [
                DateTime(2023, 1, 1, 0),
                DateTime(2023, 1, 1, 2),
                DateTime(2023, 1, 1, 4)
            ],
            ws = [10.0, missing, 15.0],
            wd = [350.0, missing, 30.0]
        )
        meso_ts_missing = TimeSeriesData(df_missing, [])
        
        ws_results_missing = interpolate_meso_values(meso_ts_missing, hours_to_test, :ws)
        @test ws_results_missing[DateTime(2023, 1, 1, 0)] ≈ 10.0
        @test ws_results_missing[DateTime(2023, 1, 1, 1)] ≈ 11.25
        @test ws_results_missing[DateTime(2023, 1, 1, 2)] ≈ 12.5
        @test ws_results_missing[DateTime(2023, 1, 1, 3)] ≈ 13.75
        @test ws_results_missing[DateTime(2023, 1, 1, 4)] ≈ 15.0
    end
end

end 