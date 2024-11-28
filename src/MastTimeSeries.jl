# 文件：./src/MastTimeSeries.jl

module MastTimeSeries

using DataFrames
using YAML
using CSV
using Dates
import ..CleanMastConfig: ProjectConfig, SensorConfig, SensorMappings

struct SensorColumn
    columnName::Symbol
    sensorType::String      # "WindSpeed" | "WindDirection" | "Temperature" | "Pressure"
    sensorDirection::String # Could be converted to Float64 later if needed
    height::Float64
    statType::String       # "avg" | "max" | "min" | "sd"
end

struct TimeSeriesData
    df::DataFrame
    sensors::Vector{SensorColumn}
end

"""
Extract placeholder names from a format string.
e.g., "Ch{channel}_{sensorType}_{height}m" -> ["channel", "sensorType", "height"]
"""
function extract_format_placeholders(format::String)::Vector{String}
    placeholders = String[]
    for m in eachmatch(r"\{([^}]+)\}", format)
        push!(placeholders, m.captures[1])
    end
    return placeholders
end

"""
Create a regex pattern from format string that captures all placeholders.
"""
function create_regex_pattern(format::String, placeholders::Vector{String})::Regex
    # Replace all placeholders with regex patterns
    regex_str = format
    
    # Create named capture groups for all placeholders
    for placeholder in placeholders
        full_placeholder = "{$placeholder}"
        regex_str = replace(regex_str, full_placeholder => "(?<$placeholder>[^_]+)")
    end
    
    # Escape special regex characters in the rest of the string
    regex_str = replace(regex_str, "." => "\\.")
    regex_str = "^" * regex_str * "\$"
    
    return Regex(regex_str)
end

"""
Parse a single column name based on format pattern.
Returns nothing if parsing fails.
"""
function parse_column_name(
    column_name::String, 
    format::String, 
    mappings::SensorMappings
)::Union{SensorColumn, Nothing}
    try
        # Find all placeholders in format
        placeholders = extract_format_placeholders(format)
        
        # Check if required fields exist in format
        if !("sensorType" in placeholders && "height" in placeholders)
            @warn "Format string must contain at least {sensorType} and {height}"
            return nothing
        end
        
        # Create regex pattern for all placeholders
        regex = create_regex_pattern(format, placeholders)
        m = match(regex, column_name)
        
        if m === nothing
            return nothing
        end
        
        # Get mapped values using the mappings from config
        sensor_type = get(mappings.sensor_types, m[:sensorType], m[:sensorType])
        
        # Parse height (remove 'm' suffix if present)
        height = parse(Float64, replace(m[:height], "m" => ""))
        
        # Get direction (default to empty string if not in format)
        direction = "sensorDirection" in placeholders ? m[:sensorDirection] : ""
        
        # Get stat type (default to "avg" if not in format)
        stat_type = if "statType" in placeholders
            get(mappings.stat_types, m[:statType], lowercase(m[:statType]))
        else
            "avg"
        end
        
        return SensorColumn(
            Symbol(column_name),
            sensor_type,
            direction,
            height,
            stat_type
        )
    catch e
        @warn "Failed to parse column $column_name" exception=e
        return nothing
    end
end

"""
Test function to demonstrate usage
"""
function test_column_parsing()
    # Example format strings
    formats = [
        "Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}",
        "{sensorType}_{height}m_{customField}_{statType}",
        "Station1_{sensorType}_{height}m",
        "{otherField}_{sensorType}_{height}m_{sensorDirection}"
    ]
    
    # Example column names
    columns = [
        "Ch1_Anem_120.00m_ESE_Avg_m/s",
        "WindSpeed_80m_Custom_Max",
        "Station1_Temp_10m",
        "XYZ_Vane_60m_N"
    ]
    
    # Example mappings
    mappings = SensorMappings(
        Dict("Anem" => "WindSpeed", "Vane" => "WindDirection", "Temp" => "Temperature"),
        Dict("Avg" => "avg", "Max" => "max", "Min" => "min"),
        Dict()
    )
    
    # Test each format with its corresponding column
    for (fmt, col) in zip(formats, columns)
        println("\nTesting format: ", fmt)
        println("Column: ", col)
        result = parse_column_name(col, fmt, mappings)
        println("Result: ", result)
    end
end

"""
Parse all column metadata in DataFrame.
Skip columns that can't be parsed.
"""
function parse_column_metadata(
    df::DataFrame,
    sensor_config::SensorConfig
)::Vector{SensorColumn}
    metadata = SensorColumn[]
    
    for col_name in names(df)
        # Skip timestamp column
        if col_name == sensor_config.timestamp_column
            continue
        end
        
        parsed = parse_column_name(col_name, sensor_config.column_format, sensor_config.mappings)
        if !isnothing(parsed)
            push!(metadata, parsed)
        end
    end
    
    return metadata
end

"""
Try to load existing sensors.yaml from project directory.
Returns nothing if file doesn't exist or is invalid.
"""
function load_existing_sensors(project_dir::String)::Union{Vector{SensorColumn}, Nothing}
    sensors_path = joinpath(project_dir, "sensors.yaml")
    
    if !isfile(sensors_path)
        return nothing
    end
    
    try
        yaml_data = YAML.load_file(sensors_path)
        sensors = SensorColumn[]
        
        for sensor in yaml_data["sensors"]
            push!(sensors, SensorColumn(
                Symbol(sensor["columnName"]),
                sensor["sensorType"],
                sensor["sensorDirection"],
                sensor["height"],
                sensor["statType"]
            ))
        end
        
        return sensors
    catch e
        @warn "Failed to load existing sensors.yaml" exception=e
        return nothing
    end
end

"""
    normalize_timestamp!(df::DataFrame, timestamp_column_name::String)

Normalize a DataFrame by:
1. Renaming the specified timestamp column to :timestamp
2. Moving the timestamp column to the first position

Parameters:
- df: Input DataFrame
- timestamp_column_name: Name of the column to be normalized as timestamp

Returns:
- Modified DataFrame (same object, modified in-place)

Throws:
- ArgumentError if the specified column name doesn't exist in the DataFrame
"""
function normalize_timestamp!(df::DataFrame, timestamp_column_name::String)
    # Check if the column exists
    if !Symbol(timestamp_column_name) in names(df)
        throw(ArgumentError("Column '$timestamp_column_name' not found in DataFrame"))
    end
    
    # Rename the timestamp column
    rename!(df, Symbol(timestamp_column_name) => :timestamp)
    
    # If timestamp is not the first column, reorder columns
    if names(df)[1] != :timestamp
        # Get all column names
        cols = names(df)
        # Remove timestamp from current position
        filter!(x -> x != :timestamp, cols)
        # Create new column order with timestamp first
        new_order = [:timestamp; cols]
        # Reorder columns
        select!(df, new_order)
    end
    
    return df
end

"""
Process CSV file and return TimeSeriesData.
Uses existing sensors.yaml if available, otherwise parses column names.
"""
function read_mast_data(config::ProjectConfig, project_dir::String)::TimeSeriesData
    # First try to load existing sensors
    existing_sensors = load_existing_sensors(project_dir)
    
    csv_file = joinpath(project_dir, config.mast.data_path)
    
    # Get column names with correct skip rows
    column_names = CSV.getnames(csv_file; skipto=config.mast.skip_to)
    
    # Prepare types for all columns
    column_types = Dict(
        col => Union{Float64, Missing} for col in column_names
    )
    # Set timestamp column type
    column_types[Symbol(config.mast.sensor.timestamp_column)] = DateTime
    
    # Prepare all CSV reading options
    csv_opts = Dict(
        :skipto => config.mast.skip_to,
        :dateformat => config.mast.sensor.timestamp_format,
        :types => column_types
    )
    
    # Read the CSV with all options
    df = CSV.read(csv_file, DataFrame; csv_opts...)
    normalize_timestamp!(df, config.mast.sensor.timestamp_column)
    
    if !isnothing(existing_sensors)
        # Validate that all columns in sensors.yaml exist in the DataFrame
        valid_sensors = filter(s -> s.columnName ∈ names(df), existing_sensors)
        return TimeSeriesData(df, valid_sensors)
    else
        # Parse column metadata and export to sensors.yaml
        sensors = parse_column_metadata(df, config.mast.sensor)
        
        # Export sensors only if we had to parse them
        export_sensors(sensors, project_dir)
        
        return TimeSeriesData(df, sensors)
    end
end

"""
Export sensor metadata to sensors.yaml
"""
function export_sensors(sensors::Vector{SensorColumn}, project_dir::String)
    sensor_data = Dict{String, Any}[]
    
    for sensor in sensors
        push!(sensor_data, Dict(
            "columnName" => String(sensor.columnName),
            "sensorType" => sensor.sensorType,
            "sensorDirection" => sensor.sensorDirection,
            "height" => sensor.height,
            "statType" => sensor.statType
        ))
    end
    
    # Write to sensors.yaml
    open(joinpath(project_dir, "sensors.yaml"), "w") do io
        YAML.write(io, Dict("sensors" => sensor_data))
    end
end

# At the end of MastTimeSeries.jl
export SensorColumn, TimeSeriesData, read_mast_data,
       # Export parsing functions for testing
       parse_column_name, extract_format_placeholders, create_regex_pattern

end # module MastTimeSeries
