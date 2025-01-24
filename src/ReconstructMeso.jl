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
Ensure that meso_ts covers the entire time range
"""
function validate_meso_coverage(meso_ts::TimeSeriesData, time_range::TrainingTimeRange)
    meso_min = minimum(meso_ts.df.timestamp)
    meso_max = maximum(meso_ts.df.timestamp)
    
    if meso_min > time_range.min || meso_max < time_range.max
        error("Meso data must cover the entire time range. " *
              "Meso range: $(meso_min) to $(meso_max), " *
              "Required range: $(time_range.min) to $(time_range.max)")
    end
end

"""
Main function to reconstruct missing mast data using meso data
"""
function reconstruct_from_meso(
    mast_ts::TimeSeriesData,
    meso_ts::TimeSeriesData,
    time_range::Union{TimeRange, Nothing}=nothing;
    min_height::Float64=50.0
)::Tuple{TimeSeriesData, WindSpeedTrainResults, WindDirectionTrainResults}
    actual_time_range = calculate_training_timerange(mast_ts, time_range)
    validate_meso_coverage(meso_ts, actual_time_range)
    
    # Prepare mast and meso data with proper timestamps and interpolation
    complete_mast, interpolated_meso = prepare_training_data(mast_ts, meso_ts)
    
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