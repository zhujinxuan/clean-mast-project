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

struct ReconstructionResults
    successes::Vector{Dict{String, Any}}
    failures::Vector{Dict{String, Any}}
end

"""
    find_reconstruction_targets(data::TimeSeriesData, sensorType::String, statType::String, min_height::Float64)::Vector{ReconstructionTarget}

Find all sensors of a specific type and statistical type that need reconstruction in the time series data. 
The function filters sensors based on the specified sensor type, statistical type, and minimum height. 
It returns a vector of `ReconstructionTarget` objects, each representing a timestamp and the columns 
with missing values that require reconstruction.

# Arguments
- `data::TimeSeriesData`: The time series data containing sensor information.
- `sensorType::String`: The type of sensor to filter (e.g., "WindSpeed" or "WindDirection").
- `statType::String`: The statistical type of the sensor (e.g., "Mean", "Max").
- `min_height::Float64`: The minimum height of the sensors to consider.

# Returns
- `Vector{ReconstructionTarget}`: A vector of `ReconstructionTarget` objects, each containing a timestamp 
  and a list of column names with missing values.
"""
function find_reconstruction_targets(data::TimeSeriesData, sensorType::String, statType::String, min_height::Float64)::Vector{ReconstructionTarget}
    # Get relevant sensor columns
    sensor_cols = [s.columnName for s in data.sensors 
                  if s.sensorType == sensorType && 
                     s.statType == statType && 
                     s.height >= min_height]
    
    # Functional pipeline with chaining and broadcasting
    targets = [
        ReconstructionTarget(row.timestamp, missing_cols)
        for row in eachrow(data.df)
        for missing_cols in [filter(col -> ismissing(row[col]), sensor_cols)]
        if !isempty(missing_cols)
    ]
    
    return targets
end

export ReconstructedSuccess, ReconstructedFailure,
       ReconstructionTarget, find_reconstruction_targets

end 