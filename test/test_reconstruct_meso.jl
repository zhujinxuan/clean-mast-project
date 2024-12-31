module TestReconstructMeso

using Test
using Dates
using DataFrames
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, SensorColumn
using CleanMastProject.Types.ReconstructMeso: TrainingTimeRange
using CleanMastProject.Types.CleanMastConfig: TimeRange
using CleanMastProject.ReconstructMeso

@testset "ReconstructMeso" begin
    # Create mast test data with 10-minute timestamps
    mast_timestamps = collect(DateTime(2024,1,1):Minute(10):(DateTime(2025,1,1) - Second(1)))
    
    # Create meso test data with hourly timestamps
    meso_timestamps = collect(DateTime(2024,1,1):Hour(1):(DateTime(2025,1,1) - Second(1)))
    
    # Calculate time in years for the sinusoidal pattern
    mast_t_years = [(t - DateTime(2024,1,1)).value/1000/60/60/24/365.25 for t in mast_timestamps]
    meso_t_years = [(t - DateTime(2024,1,1)).value/1000/60/60/24/365.25 for t in meso_timestamps]
    w = 2π  # angular frequency for annual cycle
    
    # Create mast data with sinusoidal pattern (10-min resolution)
    mast_df = DataFrame(
        timestamp = mast_timestamps,
        ws_80m = Vector{Union{Missing, Float64}}(5.0 .+ 2.0 .* sin.(w .* mast_t_years)),
        wd_80m = Vector{Union{Missing, Float64}}([mod(180.0 + (i/2880.0), 360.0) for i in 1:length(mast_timestamps)])
    )
    # Store original unmasked data for comparison
    original_ws = copy(mast_df.ws_80m)
    original_wd = copy(mast_df.wd_80m)
    
    # Add some missing values to mast data
    missing_indices = rand(1:length(mast_timestamps), div(length(mast_timestamps), 3))
    mast_df.ws_80m[missing_indices] .= missing
    mast_df.wd_80m[missing_indices] .= missing
    
    # Create meso data with related sinusoidal pattern (hourly resolution)
    meso_df = DataFrame(
        timestamp = meso_timestamps,
        ws_75m = Vector{Union{Missing, Float64}}(3.0 .+ sin.(w .* meso_t_years)),
        wd_75m = Vector{Union{Missing, Float64}}([mod(200.0 + (i/480.0), 360.0) for i in 1:length(meso_timestamps)])
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
    
    time_range = TimeRange(DateTime(2024,1,1), DateTime(2024,12,31,23,59,59))

    @testset "reconstruct_meso" begin
        result = reconstruct_from_meso(mast_ts, meso_ts, time_range)
        
        @test size(result.df, 1) == size(mast_df, 1)
        @test all(result.df.timestamp .== mast_df.timestamp)
        @test count(ismissing, result.df.ws_80m) < count(ismissing, mast_df.ws_80m)
        @test count(ismissing, result.df.wd_80m) < count(ismissing, mast_df.wd_80m)
        
        # Test reconstructed values against original formula
        missing_mask = ismissing.(mast_df.ws_80m)
        reconstructed_ws = result.df.ws_80m[missing_mask]
        original_ws_masked = original_ws[missing_mask]
        
        # Test if reconstructed wind speed is within 0.2 m/s
        @test all(abs.(reconstructed_ws .- original_ws_masked) .< 0.01)
        
        # Test wind direction reconstruction 
        missing_mask_wd = ismissing.(mast_df.wd_80m)
        reconstructed_wd = result.df.wd_80m[missing_mask_wd]
        original_wd_masked = original_wd[missing_mask_wd]
        
        # Handle circular nature of wind direction
        wd_diff = abs.(reconstructed_wd .- original_wd_masked)
        wd_diff = min.(wd_diff, 360.0 .- wd_diff)
        @test all(wd_diff .< 1.0)
    end
end

end 