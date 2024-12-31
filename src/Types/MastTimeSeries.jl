module MastTimeSeries

using DataFrames
import ..Types.Utils: from_dict, to_dict

# Define valid stat types
@enum StatType begin
    avg
    max
    min
    sd
end

# String conversion for StatType
const STAT_TYPE_STRINGS = Dict(
    avg => "avg",
    max => "max",
    min => "min",
    sd => "sd"
)

const STAT_TYPE_FROM_STRING = Dict(v => k for (k, v) in STAT_TYPE_STRINGS)

struct SensorColumn
    columnName::Symbol
    sensorType::String      # "WindSpeed" | "WindDirection" | "Temperature" | "Pressure"
    sensorDirection::String # Could be converted to Float64 later if needed
    height::Float64
    statType::StatType     # Using enum instead of String
    unit::String
    
    function SensorColumn(columnName::Symbol, sensorType::String, sensorDirection::String, 
                         height::Float64, statType::String, unit::String)
        if !haskey(STAT_TYPE_FROM_STRING, statType)
            throw(ArgumentError("Invalid statType: $statType. Must be one of: $(join(values(STAT_TYPE_STRINGS), ", "))"))
        end
        new(columnName, sensorType, sensorDirection, height, STAT_TYPE_FROM_STRING[statType], unit)
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
        "statType" => STAT_TYPE_STRINGS[s.statType],
        "unit" => s.unit
    )
end

export SensorColumn, TimeSeriesData, StatType, avg, max, min, sd

end # module 