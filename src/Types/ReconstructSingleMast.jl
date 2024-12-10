module ReconstructSingleMast

using Dates
using ..MastTimeSeries

struct ReconstructionTarget
    timestamp::DateTime
    columns::Vector{Symbol}
end

struct ReconstructedSuccess
    timestamp::DateTime
    columnName::Symbol
    value::Float64
end

struct ReconstructedFailure
    timestamp::DateTime
    columnName::Symbol
    reason::String
end

struct WindSpeedProfile
    reference_height::Float64 # Default is 50m
    shear_exponent::Float64
end

struct DirectionCorrelation
    source_height::Float64
    target_height::Float64
    mean_difference::Float64  # Average directional difference
end

"""
    find_reconstruction_targets(data::TimeSeriesData, sensorType::String)::Vector{ReconstructionTarget}

Find all sensors of a specific type that need reconstruction in the time series data.
sensorType can be "WindSpeed" or "WindDirection"
"""
function find_reconstruction_targets(data::TimeSeriesData, sensorType::String, statType::String, min_height::Float64)::Vector{ReconstructionTarget}
    # Get relevant sensor columns
    sensor_cols = [s.columnName for s in data.sensors 
                  if s.sensorType == sensorType && 
                     s.statType == statType && 
                     s.height >= min_height]
    
    # Find timestamps with missing values
    targets = ReconstructionTarget[]
    for row in eachrow(data.df)
        missing_cols = filter(col -> ismissing(row[col]), sensor_cols)
        if !isempty(missing_cols)
            push!(targets, ReconstructionTarget(row.timestamp, missing_cols))
        end
    end
    
    return targets
end

export ReconstructedSuccess, ReconstructedFailure, WindSpeedProfile, DirectionCorrelation,
       ReconstructionTarget, find_reconstruction_targets

end 