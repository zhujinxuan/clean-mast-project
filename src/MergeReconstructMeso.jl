"""
    MergeReconstructMeso.jl

Module for merging reconstructed mesoscale data with mast data, handling both wind speed
and direction reconstructions.
"""
module MergeReconstructMeso

using DataFrames
using Dates
using ..Types.MastTimeSeries: TimeSeriesData, TimeRange
using ..TimeSeriesProcessing.Regularization: ensure_regular_intervals, validate_intervals
using ..TimeSeriesProcessing.Interpolation: interpolate_timeseries
using ..Types.MastReferenceModel: ReconstructionPayload, ReconstructionSource, merge_reconstruct!, AbstractMastReferenceModel, getModelName, reconstruct

export merge_reconstruct_meso

"""
    prepare_merge_data(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData, reconstruction_time_range::TimeRange)::Tuple{TimeSeriesData, TimeSeriesData}

Prepare mast and meso data for merging by aligning timestamps and ensuring regular intervals.

# Arguments
- `mast_ts::TimeSeriesData`: Original mast time series
- `meso_ts::TimeSeriesData`: Reconstructed mesoscale time series

# Returns
- `Tuple{TimeSeriesData, TimeSeriesData}`: Processed (mast_ts, meso_ts) pair with aligned timestamps
"""
function prepare_merge_data(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData, reconstruction_time_range::TimeRange)::Tuple{TimeSeriesData, TimeSeriesData}
    
    # Ensure mast data has regular 10-minute intervals
    mast_ts = ensure_regular_intervals(mast_ts, reconstruction_time_range, Minute(10))
    
    # Ensure meso data matches mast timestamps exactly
    meso_ts = interpolate_timeseries(meso_ts, mast_ts.df.timestamp)
    
    return mast_ts, meso_ts
end

"""
    merge_reconstruct_meso(mast_payload::ReconstructionPayload, meso::TimeSeriesData, 
                        model:: AbstractMastReferenceModel, reconstruction_time_range::TimeRange)::ReconstructionPayload
"""
function merge_reconstruct_meso(mast_payload::ReconstructionPayload, meso::TimeSeriesData, 
    model::AbstractMastReferenceModel, reconstruction_time_range::TimeRange)::ReconstructionPayload
    # Prepare data for merging
    prepared_mast, prepared_meso = prepare_merge_data(mast_payload.data, meso, reconstruction_time_range)
    # Create reconstructed meso data
    reconstructed_meso = reconstruct(model, prepared_meso)

    mast_payload = ReconstructionPayload(prepared_mast, mast_payload.reconstruction_sources)
    # Merge reconstructed data, tracking sources
    merge_reconstruct!(mast_payload, reconstructed_meso, "meso", getModelName(model))
    return mast_payload
end

end # module 