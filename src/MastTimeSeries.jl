# 文件：./src/MastTimeSeries.jl

module MastTimeSeries

using DataFrames
using YAML
using CSV
using Dates
using ..Types.Utils: from_dict, to_dict
using ..Types.MastTimeSeries: SensorColumn, TimeSeriesData, ParsedSensor
using ..SensorParser: normalize_timestamp!, apply_multipliers!, parse_column_metadata
import ..Types.CleanMastConfig: MappingRule, RuleOutcome, SensorConfig, MastConfig, MesoConfig

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
        
        sensor = ParsedSensor(
            Symbol(new_column_name),
            format,              # Store the format used
            something(rule_outcome.sensorType, input["sensorType"]),
            sensorDirection,
            something(rule_outcome.height, input["height"]),
            something(rule_outcome.statType, get(input, "statType", "avg")),
            something(rule_outcome.unit, get(input, "unit", "")),
            originalColumnName=Symbol(column_name),
            multiplier=rule_outcome.multiplier
        )
        
        return sensor::Union{ParsedSensor, Nothing}
    end
    
    return nothing::Union{ParsedSensor, Nothing}
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
Export sensor metadata to sensors.yaml
"""
function export_sensors(sensors::Vector{T}, project_dir::String) where T <: Union{SensorColumn, ParsedSensor}
    sensor_data = [to_dict(sensor) for sensor in sensors]
    
    # Write to sensors.yaml
    open(joinpath(project_dir, "sensors.yaml"), "w") do io
        YAML.write(io, Dict("sensors" => sensor_data))
    end
end


# At the end of MastTimeSeries.jl
export TimeSeriesData

end # module MastTimeSeries
