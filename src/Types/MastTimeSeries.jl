module MastTimeSeries

using DataFrames
import ..Types.Utils: from_dict, to_dict

struct SensorColumn
    columnName::Symbol
    originalColumnName::Symbol  # Track the original column name before unit transformation
    sensorType::String      # "WindSpeed" | "WindDirection" | "Temperature" | "Pressure"
    sensorDirection::String
    height::Float64
    statType::String     # Changed from StatType enum to String
    unit::String
    multiplier::Union{Float64, Nothing}
    
    function SensorColumn(columnName::Symbol, originalColumnName::Symbol, sensorType::String, sensorDirection::String, 
                         height::Float64, statType::String, unit::String, 
                         multiplier::Union{Float64, Nothing}=nothing)
        new(columnName, originalColumnName, sensorType, sensorDirection, height, statType, unit, multiplier)
    end

    # Convenience constructor when original and new names are the same
    function SensorColumn(columnName::Symbol, sensorType::String, sensorDirection::String, 
                         height::Float64, statType::String, unit::String, 
                         multiplier::Union{Float64, Nothing}=nothing)
        new(columnName, columnName, sensorType, sensorDirection, height, statType, unit, multiplier)
    end
end

"""
Find nearest height sensor of specified type in sensors list
"""
function find_nearest_height_sensor(target_height::Float64, sensors::Vector{SensorColumn}, 
                                  sensor_type::String, stat_type::String="avg")::Union{SensorColumn, Nothing}
    matching_sensors = filter(s -> s.sensorType == sensor_type && s.statType == stat_type, sensors)
    isempty(matching_sensors) && return nothing
    
    # Find sensor with closest height
    closest_sensor = reduce((s1, s2) -> 
        abs(s1.height - target_height) < abs(s2.height - target_height) ? s1 : s2, 
        matching_sensors)
    
    return closest_sensor
end

struct TimeSeriesData
    df::DataFrame
    sensors::Vector{SensorColumn}
end

"""
Convert a dictionary to a SensorColumn
"""
function from_dict(::Type{SensorColumn}, d::Dict{String, Any})::SensorColumn
    columnName = Symbol(d["columnName"])
    originalColumnName = get(d, "originalColumnName", columnName)
    SensorColumn(
        columnName,
        Symbol(originalColumnName),
        d["sensorType"],
        d["sensorDirection"],
        d["height"],
        d["statType"],
        d["unit"],
        get(d, "multiplier", nothing)
    )
end

"""
Convert a SensorColumn to a dictionary
"""
function to_dict(s::SensorColumn)::Dict{String, Any}
    Dict{String, Any}(
        "columnName" => String(s.columnName),
        "originalColumnName" => String(s.originalColumnName),
        "sensorType" => s.sensorType,
        "sensorDirection" => s.sensorDirection,
        "height" => s.height,
        "statType" => s.statType,
        "unit" => s.unit,
        "multiplier" => s.multiplier
    )
end

export SensorColumn, TimeSeriesData

end # module 