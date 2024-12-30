using Test
using ...Types.ReconstructMeso: TrainingTimeRange

include("./ReconstructMeso/test_data_processing.jl")
include("./ReconstructMeso/test_training.jl")
include("./ReconstructMeso/test_reconstruction.jl")

@testset "ReconstructMeso" begin
    # Create test data for full integration test
    timestamps = DateTime(2024,1,1):Hour(1):DateTime(2024,1,10)
    time_range = TrainingTimeRange(DateTime(2024,1,1), DateTime(2024,1,10))
    
    # Mast data with missing values
    mast_df = DataFrame(
        timestamp = timestamps,
        ws_80m = vcat(fill(missing, 24), collect(5.0:0.5:15.0), fill(missing, 24)),
        wd_80m = vcat(fill(missing, 24), collect(180.0:5.0:270.0), fill(missing, 24))
    )
    
    # Meso data (complete)
    meso_df = DataFrame(
        timestamp = timestamps,
        ws_75m = collect(2.0:0.25:7.0),
        wd_75m = collect(175.0:2.5:265.0)
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
    
    @testset "reconstruct_from_meso" begin
        result = reconstruct_from_meso(mast_ts, meso_ts, time_range)
        
        # Check that we have no missing values in the reconstruction period
        @test !any(ismissing, result.df[25:72, :ws_80m])
        @test !any(ismissing, result.df[25:72, :wd_80m])
        
        # Check that correlations are reasonable
        ws_corr = cor(skipmissing(result.df.ws_80m), meso_df.ws_75m)
        @test ws_corr > 0.8
        
        # Check that wind directions are within reasonable range
        wd_diff = mean(abs.(skipmissing(result.df.wd_80m .- meso_df.wd_75m)))
        @test wd_diff < 20.0  # Average difference should be less than 20 degrees
    end
end 