module ReconstructMeso

using ..Types.MastTimeSeries: TimeSeriesData
using ..Types.CleanMastConfig: TimeRange
using ..Types.ReconstructMeso: WindSpeedTrainResults, WindDirectionTrainResults, TrainingTimeRange
using Dates


include("./ReconstructMeso/DataProcessing.jl")
include("./ReconstructMeso/Training.jl")
include("./ReconstructMeso/Reconstruction.jl")
using .DataProcessing
using .Training
using .Reconstruction

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
    actual_time_range = calculate_training_timerange(mast_ts, time_range)
    
    # Prepare complete timeseries first
    complete_mast = DataProcessing.prepare_timeseries(mast_ts, actual_time_range, Minute(10))
    complete_meso = DataProcessing.prepare_timeseries(meso_ts, actual_time_range, Minute(60))
    
    # Average data for training
    avg_mast = DataProcessing.average_timeseries(complete_mast, actual_time_range, training_period_days)
    avg_meso = DataProcessing.average_timeseries(complete_meso, actual_time_range, training_period_days)
    
    # Train correlations
    ws_results = Training.train_wind_speed(avg_mast, avg_meso, min_height)
    wd_results = Training.train_wind_direction(avg_mast, avg_meso, min_height)
    
    # Fill missing data
    Reconstruction.fill_missing_data(complete_mast, complete_meso, actual_time_range, ws_results, wd_results)
end

export reconstruct_from_meso, default_time_range

end 