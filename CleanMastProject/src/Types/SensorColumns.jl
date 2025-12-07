module SensorColumns

using DataFrames
import ..Utils: from_dict, to_dict
using Parameters

struct ParsedSensor
    columnName::Symbol
    originalColumnNames::Vector{Symbol}  # Track original column names (supports merging)
    columnFormat::String       # Store the format used to create this column
    sensorType::String      # "WindSpeed" | "WindDirection" | "Temperature" | "Pressure"
    sensorDirection::String
    height::Float64
    statType::String     # Changed from StatType enum to String
    unit::String
    multiplier::Union{Float64, Nothing}

    function ParsedSensor(columnName::Symbol,
                         columnFormat::String,
                         sensorType::String,
                         sensorDirection::String,
                         height::Float64,
                         statType::String,
                         unit::String;
                         originalColumnNames::Union{Symbol, Vector{Symbol}}=columnName,
                         multiplier::Union{Float64, Nothing}=nothing)
        # Convert single Symbol to Vector for consistency
        orig_names = originalColumnNames isa Symbol ? [originalColumnNames] : originalColumnNames
        new(columnName, orig_names, columnFormat, sensorType, sensorDirection, height, statType, unit, multiplier)
    end
end

@with_kw struct SensorColumn
    columnName::Symbol
    sensorType::String
    sensorDirection::String
    height::Float64
    statType::String
    unit::String
end

function to_SensorColumn(parsed_sensor::ParsedSensor)::SensorColumn
    return SensorColumn(
        parsed_sensor.columnName,
        parsed_sensor.sensorType,
        parsed_sensor.sensorDirection,
        parsed_sensor.height,
        parsed_sensor.statType,
        parsed_sensor.unit
    )
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

"""
Create standardized sensor short name for reports following the naming conventions:
- For statType = "avg": {shortName}:{height}m:{direction} or {shortName}:{height}m (if direction is "N/A")
- For other statType: {shortName}:{height}m:{direction}:{statType} or {shortName}:{height}m:{statType} (if direction is "N/A")

Modified for Typst compatibility:
- Replaces underscores (_) and other non-alphanumeric characters with hyphens (-)
- Trims trailing non-alphanumeric characters to ensure names end with digits or letters
"""
function create_sensor_short_name(sensor::SensorColumn)::String
    # Map sensor types to short names
    short_name = get_sensor_style_short_name(sensor.sensorType)

    # Format height as integer if it's a whole number, otherwise as float
    height_str = sensor.height == floor(sensor.height) ? string(Int(sensor.height)) : string(sensor.height)

    # Base name with height
    base_name = "$(short_name):$(height_str)m"

    # Handle direction
    has_direction = sensor.sensorDirection != "N/A"
    direction_part = has_direction ? ":$(sensor.sensorDirection)" : ""

    # Handle statType
    full_name = if sensor.statType == "avg"
        # For average sensors, don't include statType
        base_name * direction_part
    else
        # For non-average sensors, include statType
        base_name * direction_part * ":$(sensor.statType)"
    end

    # Make Typst-compatible
    return make_typst_compatible_name(full_name)
end

"""
Map sensor type to standardized short name
"""
function get_sensor_style_short_name(sensor_type::String)::String
    type_mapping = Dict(
        "WindSpeed" => "WS",
        "WindDirection" => "WD", 
        "Temperature" => "TEMP",
        "Pressure" => "PRES",
        "Humidity" => "HUM",
        "SolarRadiation" => "RAD",
        "Precipitation" => "PREC"
    )
    
    return get(type_mapping, sensor_type, sensor_type)
end

"""
Make a sensor name Typst-compatible by:
1. Replacing underscores and other non-alphanumeric characters (except : and .) with hyphens
2. Trimming trailing non-alphanumeric characters to ensure names end with digits or letters
"""
function make_typst_compatible_name(name::String)::String
    # Replace underscores and other problematic characters with hyphens
    # Keep colons (:) and dots (.) as they're used in the naming scheme
    typst_name = replace(name, r"[^a-zA-Z0-9:./-]" => "-")

    # Trim trailing non-alphanumeric characters (but preserve internal structure)
    typst_name = replace(typst_name, r"[^a-zA-Z0-9]+$" => "")

    return typst_name
end

"""
Convert a dictionary to a ParsedSensor
"""
function from_dict(::Type{ParsedSensor}, d::Dict{String, Any})::ParsedSensor
    columnName = Symbol(d["columnName"])
    columnFormat = get(d, "columnFormat", "")  # Default to empty string if not provided

    # Handle both old (originalColumnName) and new (originalColumnNames) formats
    originalColumnNames = if haskey(d, "originalColumnNames")
        [Symbol(name) for name in d["originalColumnNames"]]
    elseif haskey(d, "originalColumnName")
        [Symbol(d["originalColumnName"])]
    else
        [columnName]
    end

    ParsedSensor(
        columnName,
        columnFormat,
        d["sensorType"],
        d["sensorDirection"],
        d["height"],
        d["statType"],
        d["unit"],
        originalColumnNames=originalColumnNames,
        multiplier=get(d, "multiplier", nothing)
    )
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
Convert a ParsedSensor to a dictionary
"""
function to_dict(s::ParsedSensor)::Dict{String, Any}
    Dict{String, Any}(
        "columnName" => String(s.columnName),
        "originalColumnNames" => [String(name) for name in s.originalColumnNames],
        "columnFormat" => s.columnFormat,
        "sensorType" => s.sensorType,
        "sensorDirection" => s.sensorDirection,
        "height" => s.height,
        "statType" => s.statType,
        "unit" => s.unit,
        "multiplier" => s.multiplier
    )
end

"""
Convert a SensorColumn to a dictionary
"""
function to_dict(s::SensorColumn)::Dict{String, Any}
    Dict{String, Any}(
        String(field) => getfield(s, field) isa Symbol ? String(getfield(s, field)) : getfield(s, field)
        for field in fieldnames(SensorColumn)
    )
end

export ParsedSensor, SensorColumn, to_SensorColumn, find_nearest_height_sensor, create_sensor_short_name, get_sensor_style_short_name, make_typst_compatible_name, from_dict, to_dict

end # module 