# 文件：./src/MastTimeSeries.jl

module MastTimeSeries

using DataFrames
using YAML
using CSV
using Dates
import ..Types.CleanMastConfig: ProjectConfig, SensorConfig, MappingRule, apply_mapping

struct SensorColumn
    columnName::Symbol
    sensorType::String      # "WindSpeed" | "WindDirection" | "Temperature" | "Pressure"
    sensorDirection::String # Could be converted to Float64 later if needed
    height::Float64
    statType::String       # "avg" | "max" | "min" | "sd"
    unit::String
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
    rules::Vector{MappingRule}
)::Union{SensorColumn, Nothing}
        placeholders = extract_format_placeholders(format)
        
        if !("sensorType" in placeholders && "height" in placeholders)
            @warn "Format string must contain at least {sensorType} and {height}"
            return nothing
        end
        
        regex = create_regex_pattern(format, placeholders)
        m = match(regex, column_name)
        
        m === nothing && return nothing
        
        # Parse input dictionary from regex matches
        input = Dict{String, Any}(
            placeholder => placeholder == "height" ? 
                parse(Float64, replace(m[Symbol(placeholder)], "m" => "")) :
                string(m[Symbol(placeholder)])
            for placeholder in placeholders
        )
        
        # Apply mapping rules and create SensorColumn
        rule_outcome = apply_mapping(rules, input)
        
        return SensorColumn(
            Symbol(column_name),
            something(rule_outcome.sensorType, input["sensorType"]),
            something(rule_outcome.sensorDirection, get(input, "sensorDirection", "")),
            something(rule_outcome.height, input["height"]),
            something(rule_outcome.statType, get(input, "statType", "avg")),
            something(rule_outcome.unit, get(input, "unit", ""))
        )
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
    
    !isfile(sensors_path) && return nothing
    
    yaml_data = YAML.load_file(sensors_path)
    
    # Convert each sensor dict to SensorColumn using map
    return map(yaml_data["sensors"]) do sensor
        SensorColumn(
            Symbol(sensor["columnName"]),
            sensor["sensorType"],
            sensor["sensorDirection"],
            sensor["height"],
            sensor["statType"],
            sensor["unit"]
        )
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
    if !((timestamp_column_name) in names(df))
        throw(ArgumentError("Column '$timestamp_column_name' not found in DataFrame"))
    end
    
    # Rename the timestamp column
    rename!(df, Symbol(timestamp_column_name) => :timestamp)
    
    # If timestamp is not the first column, reorder columns
    if names(df)[1] != "timestamp"
        # Get all column names
        cols = Symbol.(names(df))
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
Find the line number where consecutive regex patterns match.
Returns the last matching line number.
"""
function find_skip_line(file_path::String, patterns::Vector{String})::Int
    current_pattern_idx = 1
    last_match_line = 0
    
    return open(file_path) do file
        for (line_num, line) in enumerate(eachline(file))
            if occursin(string_to_regex_or_string(patterns[current_pattern_idx]), line)
                if current_pattern_idx == length(patterns) 
                    return line_num  # Found all patterns consecutively
                end
                current_pattern_idx += 1
                last_match_line = line_num
            else
                # Reset if we break the consecutive pattern
                current_pattern_idx = 1
                # Check if the current line matches the first pattern
                if occursin(string_to_regex_or_string(patterns[1]), line)
                    current_pattern_idx = 2
                    last_match_line = line_num
                end
            end
        end
        throw(ErrorException("Could not find consecutive matches for all patterns"))
    end
end

"""
Convert string to Regex if it's enclosed in forward slashes, otherwise return the string as is.
Example: "/pattern/" -> Regex("pattern"), "," -> ","
"""
function string_to_regex_or_string(s::String)::Union{Regex,String}
    if startswith(s, "/") && endswith(s, "/")
        return Regex(s[2:end-1])  # Remove the slashes and convert to Regex
    end
    return s
end

"""
Generate CSV reading options based on configuration and column names.
"""
function generate_csv_opts(config::ProjectConfig, project_dir::String)::Dict{Symbol, Any}
    csv_file = joinpath(project_dir, config.mast.data_path)
    
    # Determine skip_to value
    skip_to = if config.mast.skip_to isa Vector{String}
        find_skip_line(csv_file, config.mast.skip_to)
    else
        config.mast.skip_to::Int
    end
    
    # Prepare the delimiter
    delim = if !isnothing(config.mast.delim)
        string_to_regex_or_string(config.mast.delim)
    else
        ','  # Default delimiter
    end
    
    # Use CSV.File to read the file and extract column names
    file = CSV.File(csv_file; header=skip_to, delim=delim)
    column_names = propertynames(file)
    
    # Prepare types for all columns
    column_types = Dict{Symbol, Type}(
        col => Union{Float64, Missing} for col in column_names
    )
    # Set timestamp column type 
    column_types[Symbol(config.mast.sensor.timestamp_column)] = DateTime
    
    # Build options dictionary
    opts = Dict{Symbol, Any}(
        :skipto => skip_to+1,
        :header=> skip_to,
        :dateformat => config.mast.sensor.timestamp_format,
        :types => column_types,
        :delim => delim
    )
    
    return opts
end

"""
Process CSV file and return TimeSeriesData.
Uses existing sensors.yaml if available, otherwise parses column names.
"""
function read_mast_data(config::ProjectConfig, project_dir::String)::TimeSeriesData
    # First try to load existing sensors
    existing_sensors = load_existing_sensors(project_dir)
    
    csv_file = joinpath(project_dir, config.mast.data_path)
    
    # Generate CSV options (now takes project_dir instead of column_names)
    csv_opts = generate_csv_opts(config, project_dir)
    
    # Read the CSV with all options
    df = CSV.read(csv_file, DataFrame; csv_opts...)
    normalize_timestamp!(df, config.mast.sensor.timestamp_column)
    
    if !isnothing(existing_sensors)
        # Validate that all columns in sensors.yaml exist in the DataFrame
        valid_sensors = filter(s -> s.columnName ∈ Symbol.(names(df)), existing_sensors)
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
            "statType" => sensor.statType,
            "unit" => sensor.unit
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
