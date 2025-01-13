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
    min_height::Float64=50.0
)::Tuple{TimeSeriesData, WindSpeedTrainResults, WindDirectionTrainResults}
    # Calculate training time range
    actual_time_range = calculate_training_timerange(mast_ts, time_range)
    
    # Prepare mast and meso data with proper timestamps and interpolation
    complete_mast, interpolated_meso = prepare_training_data(mast_ts, meso_ts, actual_time_range)
    
    # Train correlations
    ws_results = Training.train_wind_speed(complete_mast, interpolated_meso, min_height)
    wd_results = Training.train_wind_direction(complete_mast, interpolated_meso, min_height)
    
    # Fill missing data
    reconstructed = Reconstruction.fill_missing_data(
        complete_mast, 
        interpolated_meso, 
        actual_time_range, 
        ws_results, 
        wd_results
    )
    
    return reconstructed, ws_results, wd_results
end

export reconstruct_from_meso

end 