module TestReconstructMeso

using Test
using Dates
using DataFrames
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, SensorColumn
using CleanMastProject.Types.ReconstructMeso: TrainingTimeRange
using CleanMastProject.Types.CleanMastConfig: TimeRange
using CleanMastProject.ReconstructMeso

@testset "ReconstructMeso" begin
    # Create test data with 10-minute timestamps
    timestamps = collect(DateTime(2024,1,1):Minute(10):DateTime(2024,1,10))
    
    # Create mast data with some missing values
    # Convert index to hours for wind patterns (i/6 since there are 6 10-min periods per hour)
    mast_df = DataFrame(
        timestamp = timestamps,
        ws_80m = Vector{Union{Missing, Float64}}([5.0 + (i÷6) + rand() for i in 1:length(timestamps)]),
        wd_80m = Vector{Union{Missing, Float64}}([mod(180.0 + (i÷6), 360.0) for i in 1:length(timestamps)])
    )
    
    # Add some missing values
    missing_indices = rand(1:length(timestamps), div(length(timestamps), 3))
    mast_df.ws_80m[missing_indices] .= missing
    mast_df.wd_80m[missing_indices] .= missing
    
    # Create meso data (complete)
    meso_df = DataFrame(
        timestamp = timestamps,
        ws_75m = Vector{Union{Missing, Float64}}([2.0 + i + 0.5*rand() for i in 1:length(timestamps)]),
        wd_75m = Vector{Union{Missing, Float64}}([mod(175.0 + i, 360.0) for i in 1:length(timestamps)])
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
    
    time_range = TimeRange(DateTime(2024,1,1), DateTime(2024,1,10))

    @testset "reconstruct_meso" begin
        result = reconstruct_from_meso(mast_ts, meso_ts, time_range)
        
        @test size(result.df, 1) == size(mast_df, 1)
        @test all(result.df.timestamp .== mast_df.timestamp)
        @test count(ismissing, result.df.ws_80m) < count(ismissing, mast_df.ws_80m)
        @test count(ismissing, result.df.wd_80m) < count(ismissing, mast_df.wd_80m)
    end
end

end 