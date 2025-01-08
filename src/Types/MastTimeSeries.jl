module MastTimeSeries

using DataFrames
import ..Types.Utils: from_dict, to_dict

struct SensorColumn
    columnName::Symbol
    sensorType::String      # "WindSpeed" | "WindDirection" | "Temperature" | "Pressure"
    sensorDirection::String
    height::Float64
    statType::String     # Changed from StatType enum to String
    unit::String
    
    function SensorColumn(columnName::Symbol, sensorType::String, sensorDirection::String, 
                         height::Float64, statType::String, unit::String)
        new(columnName, sensorType, sensorDirection, height, statType, unit)
    end
end

struct TimeSeriesData
    df::DataFrame
    sensors::Vector{SensorColumn}
end

"""
Convert a dictionary to a SensorColumn
"""
function from_dict(::Type{SensorColumn}, d::Dict{String, Any})::SensorColumn
    SensorColumn(
        Symbol(d["columnName"]),
        d["sensorType"],
        d["sensorDirection"],
        d["height"],
        d["statType"],
        d["unit"]
    )
end

"""
Convert a SensorColumn to a dictionary
"""
function to_dict(s::SensorColumn)::Dict{String, Any}
    Dict{String, Any}(
        "columnName" => String(s.columnName),
        "sensorType" => s.sensorType,
        "sensorDirection" => s.sensorDirection,
        "height" => s.height,
        "statType" => s.statType,
        "unit" => s.unit
    )
end

export SensorColumn, TimeSeriesData

end # module 