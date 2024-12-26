module ReconstructMeso

using ..Types.MastTimeSeries: TimeSeriesData
using ..Types.CleanMastConfig: TimeRange
using ..Types.ReconstructMeso: WindSpeedTrainResults, WindDirectionTrainResults
using Dates

include("./ReconstructMeso/DataProcessing.jl")
include("./ReconstructMeso/Training.jl")
include("./ReconstructMeso/Reconstruction.jl")

"""
Calculate default time range for reconstruction (1 year before latest timestamp)
"""
function default_time_range(mast_ts::TimeSeriesData)::TimeRange
    latest = maximum(mast_ts.df.timestamp)
    TimeRange(
        latest - Year(1),  # start from 1 year before latest
        latest             # end at latest timestamp
    )
end

"""
Main function to reconstruct missing mast data using meso data
"""
function reconstruct_from_meso(
    mast_ts::TimeSeriesData,
    meso_ts::TimeSeriesData,
    time_range::Union{TimeRange, Nothing}=nothing;
    training_period_days::Int=15,
    min_height::Float64=50.0
)::TimeSeriesData
    # Use default time range if none provided
    actual_time_range = isnothing(time_range) ? default_time_range(mast_ts) : time_range
    
    # Average data for training
    avg_mast = DataProcessing.average_timeseries(mast_ts, actual_time_range, training_period_days)
    avg_meso = DataProcessing.average_timeseries(meso_ts, actual_time_range, training_period_days)
    
    # Train correlations
    ws_results = Training.train_wind_speed(avg_mast, avg_meso, min_height)
    wd_results = Training.train_wind_direction(avg_mast, avg_meso, min_height)
    
    # Fill missing data
    Reconstruction.fill_missing_data(mast_ts, meso_ts, actual_time_range, ws_results, wd_results)
end

export reconstruct_from_meso, default_time_range

end 