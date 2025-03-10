module SensorParser

using DataFrames
using YAML
using CSV
using Dates
using ..Types.Utils: from_dict, to_dict
using ..Types.MastTimeSeries: SensorColumn, TimeSeriesData, ParsedSensor
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
)::Union{ParsedSensor, Nothing}
    # Try each format pattern
    for format in formats
        # Extract placeholders from format
        placeholders = extract_format_placeholders(format)
        
        if !("sensorType" in placeholders && "height" in placeholders)
            @warn "Format string must contain at least {sensorType} and {height}: $format"
            continue
        end
        
        # Create regex pattern
        pattern = create_regex_pattern(format, placeholders)
        
        # Try to match column name against pattern
        m = match(pattern, column_name)
        isnothing(m) && continue
        
        # Extract captured values
        input = Dict{String, Any}()
        for placeholder in placeholders
            value = m[placeholder]
            
            # Convert height to Float64 if possible
            if placeholder == "height"
                try
                    value = parse(Float64, replace(value, "m" => ""))
                catch
                    @warn "Failed to parse height value: $value"
                    continue
                end
            end
            
            input[placeholder] = value
        end
        
        # Apply mapping rules
        rule_outcome = apply_mapping(rules, input)
        
        # Create input dictionary from sensor fields and merge with rule_outcome
        input["sensorType"] = something(rule_outcome.sensorType, input["sensorType"])
        input["sensorDirection"] = get(input, "sensorDirection", "")
        input["height"] = something(rule_outcome.height, input["height"])
        input["statType"] = something(rule_outcome.statType, get(input, "statType", "avg"))
        input["unit"] = something(rule_outcome.unit, get(input, "unit", ""))

        
        # Generate new name using format and merged input
        new_column_name = format
        for (key, value) in input
            if key == "height" && floor(value) == value
                new_column_name = replace(new_column_name, "{$key}" => Int64(value))
            else
                new_column_name = replace(new_column_name, "{$key}" => value)
            end
        end
        
        # Create ParsedSensor object
        sensor = ParsedSensor(
            Symbol(new_column_name),
            format,              # Store the format used
            String(input["sensorType"]),
            String(input["sensorDirection"]),
            input["height"],
            String(input["statType"]),
            String(input["unit"]),
            originalColumnName=Symbol(column_name),
            multiplier=rule_outcome.multiplier
        )
        
        return sensor::Union{ParsedSensor, Nothing}
    end
    
    return nothing::Union{ParsedSensor, Nothing}
end

"""
Parse column metadata from DataFrame using sensor configuration.
Returns a vector of ParsedSensor objects.
"""
function parse_column_metadata(df::DataFrame, sensor_config::SensorConfig)::Vector{ParsedSensor}
    sensors = ParsedSensor[]
    
    # Process each column
    for col in names(df)
        # Skip timestamp column
        col == Symbol(sensor_config.timestamp_column) && continue
        
        # Try to parse column name
        sensor = parse_column_name(String(col), sensor_config.column_formats, sensor_config.mappings)
        
        if !isnothing(sensor)
            push!(sensors, sensor)
        else
            @warn "Failed to parse column name: $col"
        end
    end
    
    return sensors
end

"""
Normalize timestamp column to DateTime type.
"""
function normalize_timestamp!(df::DataFrame, timestamp_column::String)
    # Check for missing values in timestamp column
    missing_timestamps = count(ismissing, df[!, timestamp_column])
    if missing_timestamps > 0
        @warn "Found $missing_timestamps missing timestamps"
    end
    
    # Convert timestamp column to DateTime if it's not already
    if eltype(df[!, timestamp_column]) != DateTime
        try
            df[!, timestamp_column] = DateTime.(df[!, timestamp_column])
        catch e
            @error "Failed to convert timestamp column to DateTime" exception=e
        end
    end
    rename!(df, timestamp_column => :timestamp)
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
Generate CSV options for reading data files.
"""
function generate_csv_opts(sensor_config::SensorConfig, csv_file::String)::Dict{Symbol, Any}
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
    
    # Build options dictionary
    opts = Dict{Symbol, Any}(
        :skipto => skip_to+1,
        :header=> skip_to,
        :dateformat => sensor_config.timestamp_format,
        :delim => delim
    )
    
    return opts
end

"""
Apply multipliers to DataFrame columns based on sensor configurations.
"""
function apply_multipliers!(df::DataFrame, sensors::Vector{T}) where T <: Union{SensorColumn, ParsedSensor}
    for sensor in sensors
        if !isnothing(sensor.multiplier) && sensor.multiplier != 1.0
            df[!, sensor.columnName] .*= sensor.multiplier
        end
    end
end

"""
Apply multipliers and rename columns based on sensor configurations.
"""
function rename_and_apply_multipliers!(df::DataFrame, sensors::Vector{ParsedSensor})
    for sensor in sensors
        # Rename column if needed
        if sensor.originalColumnName != sensor.columnName
            if !(sensor.originalColumnName in propertynames(df))
                @warn "Original column $(sensor.originalColumnName) not found in DataFrame"
                continue
            end
            rename!(df, sensor.originalColumnName => sensor.columnName)
        end
    end
    # Apply multipliers
    apply_multipliers!(df, sensors)
    
    return df
end

export parse_column_metadata, normalize_timestamp!, generate_csv_opts, apply_multipliers!,
       parse_column_name, extract_format_placeholders, create_regex_pattern, find_skip_line,
       string_to_regex_or_string, rename_and_apply_multipliers!

end 