module TestReconstruction

using Test
using Dates
using DataFrames
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, SensorColumn
using CleanMastProject.Types.ReconstructMeso: TrainingTimeRange, WindSpeedTrainResult, 
                                            WindDirectionTrainResult, WindSpeedSectorModel
using CleanMastProject.ReconstructMeso.Reconstruction: fill_missing_data, get_sector_model

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
    
    # Create sector models (different correlation for each sector)
    sector_models = [
        WindSpeedSectorModel(i * 22.5, (i + 1) * 22.5, 2.0 - 0.1 * i, 1.0 + 0.2 * i)
        for i in 0:15
    ]
    
    # Create training results
    ws_results = Dict(
        :ws_80m => WindSpeedTrainResult(
            mast_sensors[1],
            meso_sensors[1],
            meso_sensors[2],
            sector_models
        )
    )
    
    wd_results = Dict(
        :wd_80m => WindDirectionTrainResult(
            mast_sensors[2],
            meso_sensors[2],
            5.0   # difference
        )
    )

    @testset "get_sector_model" begin
        # Test model selection for different directions
        for i in 0:15
            direction = i * 22.5 + 11.25  # Middle of sector
            model = get_sector_model(direction, ws_results[:ws_80m])
            
            # Check we got the right sector model
            @test model.sector_start == i * 22.5
            @test model.sector_end == (i + 1) * 22.5
            @test isapprox(model.slope, 2.0 - 0.1 * i)
            @test isapprox(model.intercept, 1.0 + 0.2 * i)
        end
        
        # Test edge cases
        @test get_sector_model(0.0, ws_results[:ws_80m]).sector_start == 0.0
        @test get_sector_model(359.9, ws_results[:ws_80m]).sector_start == 337.5
    end

    @testset "fill_missing_data" begin
        result = fill_missing_data(mast_ts, meso_ts, time_range, ws_results, wd_results)

        # Check wind speed reconstruction
        for (i, row) in enumerate(eachrow(result.df))
            if ismissing(mast_df.ws_80m[i])
                # Get the appropriate sector model
                meso_dir = meso_df.wd_75m[i]
                model = get_sector_model(meso_dir, ws_results[:ws_80m])
                
                # Calculate expected value
                meso_speed = meso_df.ws_75m[i]
                expected_ws = model.slope * meso_speed + model.intercept
                
                @test isapprox(row.ws_80m, expected_ws, atol=0.1)
            end
        end
        
        # Check wind direction reconstruction
        filled_wd = result.df[ismissing.(mast_df.wd_80m), :wd_80m]
        expected_wd = @. mod(meso_df[ismissing.(mast_df.wd_80m), :wd_75m] + 5.0, 360)
        @test all(isapprox.(filled_wd, expected_wd, atol=0.1))
    end
end

end 