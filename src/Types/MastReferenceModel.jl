"""
    MastReferenceModel.jl

Abstract types for mast reference models used in wind reconstruction from mesoscale data.
These types define the interface for training and reconstructing wind time series.
"""
module MastReferenceModel

using Dates
using DataFrames: DataFrame
using ..MastTimeSeries: TimeSeriesData
import ..Utils: show_as_dataframe

export AbstractMastReferenceModel,
       AbstractSpeedReferenceModel,
       AbstractDirectionReferenceModel,
       train,
       reconstruct,
       ReconstructionPayload,
       ReconstructionSource,
       merge_reconstruct,
       getModelName

"""
    AbstractMastReferenceModel

Base abstract type for all mast reference models used in wind reconstruction.
All concrete model types should implement:
- `train(::Type{T}, params::Dict, mast::TimeSeriesData, meso::TimeSeriesData)::T`
- `reconstruct(model::T, meso::TimeSeriesData)::TimeSeriesData`
"""
abstract type AbstractMastReferenceModel end

"""
    AbstractSpeedReferenceModel <: AbstractMastReferenceModel

Abstract type for models that reconstruct wind speed time series.
Models of this type should focus on the relationship between mesoscale 
and mast wind speed measurements.
"""
abstract type AbstractSpeedReferenceModel <: AbstractMastReferenceModel end

"""
    AbstractDirectionReferenceModel <: AbstractMastReferenceModel

Abstract type for models that reconstruct wind direction time series.
Models of this type should handle the circular nature of wind direction data
and implement appropriate transformations between mesoscale and mast measurements.
"""
abstract type AbstractDirectionReferenceModel <: AbstractMastReferenceModel end

"""
    train(::Type{T}, params::Dict, mast::TimeSeriesData, meso::TimeSeriesData)::T where {T<:AbstractMastReferenceModel}

Train a mast reference model using the provided parameters, mast data, and mesoscale data.

# Arguments
- `params::Dict`: Dictionary of parameters for the model
- `mast::TimeSeriesData`: Mast data for training
- `meso::TimeSeriesData`: Mesoscale data for training

# Returns
- `T`: Trained mast reference model
"""
function train(::Type{T}, params::P, mast::TimeSeriesData, meso::TimeSeriesData)::T where {T<:AbstractMastReferenceModel, P}
    error("train not implemented for model type $(T)")
end

"""
    reconstruct(model::T, meso::TimeSeriesData)::TimeSeriesData where {T<:AbstractMastReferenceModel}

Reconstruct mast-level time series using a trained model and mesoscale data.

# Arguments
- `model::T`: Trained mast reference model
- `meso::TimeSeriesData`: Mesoscale data for reconstruction period

# Returns
- `TimeSeriesData`: Reconstructed mast-level time series

# Requirements
- Mesoscale data must be at 10-minute intervals
- Input data must be compatible with the trained model

# Note
This is an interface declaration. Concrete subtypes must implement this method.
"""
function reconstruct(model::T, meso::TimeSeriesData)::TimeSeriesData where {T<:AbstractMastReferenceModel}
    error("reconstruct not implemented for model type $(T)")
end

"""
    ReconstructionSource

Tracks the source of a reconstructed value in the merged time series.

# Fields
- `timestamp::DateTime`: When the value was reconstructed
- `sensor_column::Symbol`: Column name in the reconstructed data
- `reference_name::String`: Reference data name, e.g. "meso"
- `model_id::String`: Identifier of the model used for reconstruction
"""
struct ReconstructionSource
    timestamp::DateTime
    sensor_column::Symbol
    reference_name::String
    model_id::String
end

"""
    ReconstructionPayload

Tracks the source of a reconstructed value in the merged time series.
"""
struct ReconstructionPayload
    data:: TimeSeriesData
    reconstruction_sources :: Vector{ReconstructionSource}
end

"""
    to_dataframe(sources::Vector{ReconstructionSource})::DataFrame

Convert a vector of ReconstructionSource to a DataFrame.

# Arguments
- `sources::Vector{ReconstructionSource}`: Vector of reconstruction sources

# Returns
- `DataFrame`: DataFrame with columns timestamp, sensor_column, reference_name, model_id
"""
function show_as_dataframe(sources::Vector{ReconstructionSource})::DataFrame
    DataFrame(
        timestamp = [s.timestamp for s in sources],
        sensor_column = [s.sensor_column for s in sources],
        reference_name = [s.reference_name for s in sources],
        model_id = [s.model_id for s in sources]
    )
end

"""
    merge_reconstruct(mast_payload::ReconstructionPayload, reconstructed::TimeSeriesData, source_id::String, model_id::String)::ReconstructionPayload

Merge reconstructed time series with original mast data, filling in missing values from the reconstructed data.

# Arguments
- `mast_payload::ReconstructionPayload`: Original mast data with missing values and reconstruction history
- `reconstructed::TimeSeriesData`: Reconstructed data to fill missing values
- `source_id::String`: Identifier of the source data (e.g. "meso")
- `model_id::String`: Identifier of the model used for reconstruction

# Returns
- `ReconstructionPayload`: Updated payload with merged data and reconstruction history

# Notes
- Original mast values are preserved where available
- Only missing values in mast data are filled from reconstructed data
- Reconstruction sources are tracked for each filled value
- Reconstructed TimeSeriesData is align with mast TimeSeriesData on timestamp
"""
function merge_reconstruct!(mast_payload::ReconstructionPayload, reconstructed::TimeSeriesData, source_id::String, model_id::String) :: ReconstructionPayload
    if !(length(reconstructed.df.timestamp) == length(mast_payload.data.df.timestamp) &&
         all(reconstructed.df.timestamp .== mast_payload.data.df.timestamp))
        throw(ArgumentError("Mismatched timestamps between reconstructed data (length $(length(reconstructed.df.timestamp))) and mast data (length $(length(mast_payload.data.df.timestamp))). Timestamps must be aligned and isomorphic."))
    end

    # Create a copy of mast data to avoid modifying original
    df = mast_payload.data.df
    
    # Find common sensors between mast and reconstructed data
    common_sensors = filter(s -> any(rs -> rs.columnName == s.columnName, reconstructed.sensors), mast_payload.data.sensors)
    
    # Process each common sensor
    for sensor in common_sensors
        col = sensor.columnName
        
        # Find rows where mast data is missing but reconstructed data is available
        missing_mask = ismissing.(df[!, col])
        
        # Only proceed if there are missing values to fill
        if any(missing_mask)
            # Fill missing values using vectorized operation
            df[missing_mask, col] .= reconstructed.df[missing_mask, col]
            
            # Track reconstruction sources for filled values
            timestamps = df.timestamp[missing_mask]
            push!(mast_payload.reconstruction_sources, 
                map(timestamp -> ReconstructionSource(timestamp, col, source_id, model_id), 
                    timestamps)...)
        end
    end

    return mast_payload
end


function getModelName(model ::AbstractMastReferenceModel)::String
    error("getModelName not implemented for $(string(typeof(model)))")
end

end