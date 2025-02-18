# 文件：./src/MastTimeSeries.jl

module MastTimeSeries

using DataFrames
using YAML
using CSV
using Dates
using ..Types.Utils: from_dict, to_dict
using ..Types.MastTimeSeries: SensorColumn, TimeSeriesData
import ..Types.CleanMastConfig: ProjectConfig, SensorConfig, MappingRule, apply_mapping, MastConfig, MesoConfig, RuleOutcome

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
Parse a single column name based on multiple format patterns.
Returns nothing if parsing fails for all formats.
"""
function parse_column_name(
    column_name::String, 
    formats::Vector{String}, 
    rules::Vector{MappingRule}
)::Union{SensorColumn, Nothing}
    # Try each format until one succeeds
    for format in formats
        placeholders = extract_format_placeholders(format)
        
        if !("sensorType" in placeholders && "height" in placeholders)
            @warn "Format string must contain at least {sensorType} and {height}: $format"
            continue
        end
        
        regex = create_regex_pattern(format, placeholders)
        m = match(regex, column_name)
        
        if isnothing(m)
            continue
        end
        
        # Parse input dictionary from regex matches
        input = Dict{String, Any}(
            placeholder => placeholder == "height" ? 
                parse(Float64, replace(m[Symbol(placeholder)], "m" => "")) :
                string(m[Symbol(placeholder)])
            for placeholder in placeholders
        )
        
        # Apply mapping rules and create SensorColumn
        rule_outcome = apply_mapping(rules, input)
        
        # Update input dictionary with rule_outcome values
        for field in fieldnames(RuleOutcome)
            value = getfield(rule_outcome, field)
            if !isnothing(value) && haskey(input, String(field))
                input[String(field)] = value
            end
        end
        
        # Generate new column name using format and updated placeholders
        new_column_name = format
        for (key, value) in input
            new_column_name = replace(new_column_name, "{$key}" => (key == "height" && floor(value) == value) ? Int64(value) : value)
        end
        
        # Add empty sensorDirection if not in format
        sensorDirection = get(input, "sensorDirection", "")
        
        sensor = SensorColumn(
            Symbol(new_column_name),
            format,              # Store the format used
            something(rule_outcome.sensorType, input["sensorType"]),
            sensorDirection,
            something(rule_outcome.height, input["height"]),
            something(rule_outcome.statType, get(input, "statType", "avg")),
            something(rule_outcome.unit, get(input, "unit", "")),
            multiplier=rule_outcome.multiplier,
            originalColumnName=Symbol(column_name)
        )
        
        return sensor::Union{SensorColumn, Nothing}
    end
    
    return nothing::Union{SensorColumn, Nothing}
end

"""
Generate a new column name for a sensor using its stored format
"""
function generate_column_name(sensor::SensorColumn)::Symbol
    # Create input dictionary from sensor fields
    input = Dict{String, Any}(
        "sensorType" => sensor.sensorType,
        "height" => sensor.height,
        "statType" => sensor.statType,
        "unit" => sensor.unit
    )
    
    # Add optional fields if they exist
    if !isempty(sensor.sensorDirection)
        input["sensorDirection"] = sensor.sensorDirection
    end
    
    # Extract channel from original name if it exists
    m = match(r"Ch(\d+)", String(sensor.originalColumnName))
    if !isnothing(m)
        input["channel"] = m.captures[1]
    end
    
    # Generate new name using format
    new_name = sensor.columnFormat
    for (key, value) in input
        new_name = replace(new_name, "{$key}" => (key == "height" && floor(value) == value) ? Int64(value) : value)
    end
    
    return Symbol(new_name)
end

"""
Get sensor configuration, loading preset if needed.
"""
function get_sensor_config(sensor_config::Union{String, SensorConfig})::SensorConfig
    if sensor_config isa String
        load_preset_format(sensor_config)
    else
        sensor_config
    end
end

"""
Parse column metadata from DataFrame using sensor configuration.
Returns a vector of SensorColumn objects.
"""
function parse_column_metadata(df::DataFrame, sensor_config::SensorConfig)::Vector{SensorColumn}
    # Skip timestamp column
    data_columns = setdiff(names(df), [sensor_config.timestamp_column, "timestamp"])
    
    # Parse each column name
    sensors = SensorColumn[]
    for column_name in data_columns
        sensor = parse_column_name(String(column_name), sensor_config.column_formats, sensor_config.mappings)
        if !isnothing(sensor)
            push!(sensors, sensor)
        else
            @warn "Failed to parse sensor column: $column_name"
        end
    end
    
    return sensors
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
function generate_csv_opts(config::Union{MastConfig, MesoConfig}, project_dir::String)::Dict{Symbol, Any}
    csv_file = joinpath(project_dir, config.data_path)
    
    # Get sensor config
    sensor_config = get_sensor_config(config.sensor)
    
    # Determine skip_to value
    skip_to = if sensor_config.skip_to isa Vector{String}
        find_skip_line(csv_file, sensor_config.skip_to)
    else
        sensor_config.skip_to::Int
    end
    
    # Prepare the delimiter
    delim = if !isnothing(sensor_config.delim)
        string_to_regex_or_string(sensor_config.delim)
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
    column_types[Symbol(sensor_config.timestamp_column)] = DateTime
    
    # Build options dictionary
    opts = Dict{Symbol, Any}(
        :skipto => skip_to+1,
        :header=> skip_to,
        :dateformat => sensor_config.timestamp_format,
        :types => column_types,
        :delim => delim
    )
    
    return opts
end

"""
Process Mast CSV file and return TimeSeriesData.
Uses existing sensors.yaml if available, otherwise parses column names.
"""
function read_mast_data(config::ProjectConfig, project_dir::String)::TimeSeriesData
    # First try to load existing sensors
    
    csv_file = joinpath(project_dir, config.mast.data_path)
    
    # Generate CSV options
    csv_opts = generate_csv_opts(config.mast, project_dir)
    
    # Read the CSV with all options
    df = CSV.read(csv_file, DataFrame; csv_opts...)
    normalize_timestamp!(df, config.mast.sensor.timestamp_column)
    
    # Parse column metadata and export to sensors.yaml
    sensors = parse_column_metadata(df, config.mast.sensor)
    
    # Export sensors only if we had to parse them
    export_sensors(sensors, project_dir)
    
    apply_multipliers!(df, sensors)
    ts = TimeSeriesData(df, sensors)
    return ts
end

"""
Process Meso CSV file and return TimeSeriesData.
Uses existing sensors.yaml if available, otherwise parses column names.
"""
function read_meso_data(config::ProjectConfig, project_dir::String)::TimeSeriesData
    csv_file = joinpath(project_dir, config.meso.data_path)
    
    # Generate CSV options
    csv_opts = generate_csv_opts(config.meso, project_dir)
    
    # Read the CSV with all options
    df = CSV.read(csv_file, DataFrame; csv_opts...)
    
    # Check for missing values in timestamp column
    missing_timestamps = count(ismissing, df[!, config.meso.sensor.timestamp_column])
    if missing_timestamps > 0
        @warn "Found $missing_timestamps missing timestamps"
    end
    
    normalize_timestamp!(df, config.meso.sensor.timestamp_column)
    
    # Parse column metadata and export to sensors.yaml
    sensors = parse_column_metadata(df, config.meso.sensor)
    
    # Apply multipliers and rename columns BEFORE creating TimeSeriesData
    apply_multipliers!(df, sensors)
    
    # Export sensors only if we had to parse them
    export_meso_sensors(sensors, project_dir)
    
    # Create TimeSeriesData object AFTER columns are renamed
    ts = TimeSeriesData(df, sensors)
    
    return ts
end

"""
Export sensor metadata to sensors.yaml
"""
function export_sensors(sensors::Vector{SensorColumn}, project_dir::String)
    sensor_data = [to_dict(sensor) for sensor in sensors]
    
    # Write to sensors.yaml
    open(joinpath(project_dir, "sensors.yaml"), "w") do io
        YAML.write(io, Dict("sensors" => sensor_data))
    end
end

"""
Export meso sensor metadata to meso-sensors.yaml
"""
function export_meso_sensors(sensors::Vector{SensorColumn}, project_dir::String)
    sensor_data = [to_dict(sensor) for sensor in sensors]
    # Write to meso-sensors.yaml
    open(joinpath(project_dir, "meso-sensors.yaml"), "w") do io
        YAML.write(io, Dict("sensors" => sensor_data))
    end
end

"""
Apply multipliers and rename columns in DataFrame based on sensor configurations.
Uses functional programming principles for efficiency.
"""
function apply_multipliers!(df::DataFrame, sensors::Vector{SensorColumn})::DataFrame
    # First handle column renames
    for sensor in sensors
        if sensor.columnName != sensor.originalColumnName
            if !hasproperty(df, sensor.originalColumnName)
                @warn "Original column $(sensor.originalColumnName) not found in DataFrame"
                continue
            end
            rename!(df, sensor.originalColumnName => sensor.columnName)
        end
    end
    
    # Then apply multipliers
    for sensor in sensors
        if !isnothing(sensor.multiplier)
            if !hasproperty(df, sensor.columnName)
                @warn "Column $(sensor.columnName) not found in DataFrame"
                continue
            end
            df[!, sensor.columnName] .*= sensor.multiplier
        end
    end
    
    return df
end

# At the end of MastTimeSeries.jl
export SensorColumn, TimeSeriesData, read_mast_data, read_meso_data,
       # Export parsing functions for testing
       parse_column_name, extract_format_placeholders, create_regex_pattern

end # module MastTimeSeries
