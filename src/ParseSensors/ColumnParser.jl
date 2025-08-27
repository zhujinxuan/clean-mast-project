# src/ParseSensors/ColumnParser.jl
"""
Core logic for parsing sensor column names based on enhanced format definitions.
"""
module ColumnParser

using ...Types.ParseSensorsConfig: SensorColumnConfig, MappingRule, RuleOutcome, apply_mapping
using ...Types.SensorColumns: ParsedSensor

export parse_column_name, create_regex_from_match, extract_format_placeholders

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
Create a regex pattern from a match string and custom placeholder patterns.
"""
function create_regex_from_match(
    match_format::String, 
    placeholders::Vector{String}, 
    patterns::Dict{String, String}
)::Regex
    regex_str = match_format
    
    # Escape special regex characters in the literal parts of the string first
    # This is a simplified approach; a more robust one would tokenize the string
    # For now, we assume placeholders don't contain special regex characters
    
    # Create named capture groups for all placeholders
    for placeholder in placeholders
        full_placeholder = "{$placeholder}"
        # Use custom pattern if available, otherwise use a generic one that disallows underscores
        pattern = get(patterns, placeholder, placeholder == "height" ? "[0-9]+\\.?[0-9]*" : "[^_]+")
        regex_str = replace(regex_str, full_placeholder => "(?<$placeholder>$pattern)")
    end
    
    # Anchor the regex
    regex_str = "^" * regex_str * "\$"
    
    return Regex(regex_str)
end

"""
    parse_column_name(column_name::String, column_configs::Vector{SensorColumnConfig}, rules::Vector{MappingRule})

Parse a single column name based on multiple `SensorColumnConfig` patterns.
Returns `nothing` if parsing fails for all formats.
"""
function parse_column_name(
    column_name::String,
    column_configs::Vector{SensorColumnConfig},
    rules::Vector{MappingRule}
)::Union{ParsedSensor, Nothing}
    for config in column_configs
        placeholders = extract_format_placeholders(config.match)
        
        # Use custom patterns if they exist
        custom_patterns = !isnothing(config.patterns) ? config.patterns.patterns : Dict{String, String}()
        pattern = create_regex_from_match(config.match, placeholders, custom_patterns)
        
        m = match(pattern, strip(column_name))
        isnothing(m) && continue
        
        # Extract captured values into a dictionary
        input = Dict{String, Any}(p => m[p] for p in placeholders)
        
        # Convert height to Float64
        if haskey(input, "height")
            try
                input["height"] = parse(Float64, replace(input["height"], "m" => ""))
            catch
                @warn "Failed to parse height value: $(input["height"])"
                continue
            end
        end
        
        # Apply mapping rules
        rule_outcome = apply_mapping(rules, input)
        
        # Combine parsed data with rule outcomes
        final_data = Dict{String, Any}(
            "sensorType" => something(rule_outcome.sensorType, input["sensorType"]),
            "sensorDirection" => something(rule_outcome.sensorDirection, get(input, "sensorDirection", "")),
            "height" => something(rule_outcome.height, get(input,"height", nothing)),
            "statType" => something(rule_outcome.statType, get(input, "statType", "avg")),
            "unit" => something(rule_outcome.unit, get(input, "unit", "")),
        )
        
        # Generate the new column name using the format string
        new_column_name = config.format
        for (key, value) in final_data
            # Handle integer heights for cleaner naming
            formatted_value = (key == "height" && floor(value) == value) ? Int64(value) : value
            new_column_name = replace(new_column_name, "{$key}" => formatted_value)
        end
        
        return ParsedSensor(
            Symbol(new_column_name),
            config.match,
            String(final_data["sensorType"]),
            String(final_data["sensorDirection"]),
            final_data["height"],
            String(final_data["statType"]),
            String(final_data["unit"]),
            originalColumnName=Symbol(column_name),
            multiplier=rule_outcome.multiplier
        )
    end
    
    return nothing
end

end 