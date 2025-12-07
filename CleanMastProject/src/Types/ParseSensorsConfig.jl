#src/Types/ParseSensorsConfig.jl
"""
Types for parse-sensors configuration, corresponding to {project}/parse-sensors.toml
"""
module ParseSensorsConfig

import ..Utils: from_dict, to_dict
using ..MastTimeSeries: TimeSeriesSource

struct RuleOutcome
    sensorType::Union{String, Nothing}
    sensorDirection::Union{String, Nothing}
    height::Union{Float64, Nothing}
    statType::Union{String, Nothing}
    unit::Union{String, Nothing}
    multiplier::Union{Float64, Nothing}
end

# Constructor for RuleOutcome with optional fields
function RuleOutcome(;
    sensorType::Union{String, Nothing}=nothing,
    sensorDirection::Union{String, Nothing}=nothing,
    height::Union{Float64, Nothing}=nothing,
    statType::Union{String, Nothing}=nothing,
    unit::Union{String, Nothing}=nothing,
    multiplier::Union{Float64, Nothing}=nothing
)
    RuleOutcome(sensorType, sensorDirection, height, statType, unit, multiplier)
end

function to_dict(r::RuleOutcome)::Dict{String, Any}
    Dict{String, Any}(
        "sensorType" => r.sensorType,
        "sensorDirection" => r.sensorDirection,
        "height" => r.height,
        "statType" => r.statType,
        "unit" => r.unit,
        "multiplier" => r.multiplier
    )
end

function from_dict(::Type{RuleOutcome}, dict::Dict{String, Any})::RuleOutcome
    RuleOutcome(
        get(dict, "sensorType", nothing),
        get(dict, "sensorDirection", nothing),
        get(dict, "height", nothing) |> h -> h isa Number ? convert(Float64, h) : nothing,
        get(dict, "statType", nothing),
        get(dict, "unit", nothing),
        get(dict, "multiplier", nothing) |> m -> m isa Number ? convert(Float64, m) : nothing
    )
end

# Define a single mapping rule
struct MappingRule
    match::Dict{String, Union{Nothing, Float64, String}}
    rule::RuleOutcome
end

# Constructor from dictionary for MappingRule
function from_dict(::Type{MappingRule}, dict::Dict{String, Any})::MappingRule
    match_dict = Dict{String, Union{Nothing, Float64, String}}(
        k => v isa Number ? convert(Float64, v) : v 
        for (k, v) in dict["match"]
    )
    
    MappingRule(match_dict, from_dict(RuleOutcome, Dict{String, Any}(dict["rule"])))
end

function to_dict(mr::MappingRule)::Dict{String, Any}
    Dict{String, Any}(
        "match" => mr.match,
        "rule" => to_dict(mr.rule)
    )
end

# Safe version of something that returns nothing if all args are nothing
safe_something(args...) = all(isnothing, args) ? nothing : something(args...)

# Functional merge for RuleOutcome
merge_outcomes(a::RuleOutcome, b::RuleOutcome)::RuleOutcome =
RuleOutcome(
            safe_something(b.sensorType, a.sensorType, nothing),
            safe_something(b.sensorDirection, a.sensorDirection, nothing),
            safe_something(b.height, a.height, nothing),
            safe_something(b.statType, a.statType, nothing),
            safe_something(b.unit, a.unit, nothing),
            safe_something(b.multiplier, a.multiplier, nothing)
           )

# Functional rule matching
function matches_rule(rule::MappingRule, input::Dict{String, Any})::Bool
    all(((k,v),) -> get(input, k, nothing) == v, pairs(rule.match))
end

# Functional apply_mapping
function apply_mapping(rules::Vector{MappingRule}, input::Dict{String, Any})::RuleOutcome
  matching_rules = filter(rule -> matches_rule(rule, input), rules)
  isempty(matching_rules) && return RuleOutcome(nothing, nothing, nothing, nothing, nothing, nothing)

  reduce(merge_outcomes, map(rule -> rule.rule, matching_rules))
end

"""
Configuration for regex patterns in sensor column matching
"""
struct PatternConfig
    patterns::Dict{String, String}  # placeholder_name => regex_pattern
end

function from_dict(::Type{PatternConfig}, dict::Dict{String, Any})::PatternConfig
    PatternConfig(Dict{String, String}(dict))
end

function to_dict(pc::PatternConfig)::Dict{String, Any}
    Dict{String, Any}(pc.patterns)
end

"""
Enhanced sensor column configuration with separate match and format patterns
"""
struct SensorColumnConfig
    match::String                           # Pattern for extracting data from column names
    format::String                          # Pattern for normalizing column names
    patterns::Union{PatternConfig, Nothing} # Optional regex patterns for placeholders
end

function from_dict(::Type{SensorColumnConfig}, dict::Dict{String, Any})::SensorColumnConfig
    patterns = if haskey(dict, "patterns")
        from_dict(PatternConfig, Dict{String, Any}(dict["patterns"]))
    else
        nothing
    end
    
    SensorColumnConfig(
        dict["match"],
        dict["format"],
        patterns
    )
end

function to_dict(scc::SensorColumnConfig)::Dict{String, Any}
    result = Dict{String, Any}(
        "match" => scc.match,
        "format" => scc.format
    )
    
    if !isnothing(scc.patterns)
        result["patterns"] = to_dict(scc.patterns)
    end
    
    result
end



"""
Enhanced sensor format configuration for TOML-based sensor definitions
"""
struct SensorFormatConfig
    columns::Vector{SensorColumnConfig}     # Column parsing configurations
    timestamp_column::String                # Name of timestamp column
    timestamp_format::Union{String, Nothing} # Optional timestamp format
    delim::Union{String, Nothing}           # Optional delimiter
    skip_to::Union{Int64, Nothing}          # Optional lines to skip
    mappings::Vector{MappingRule}           # Mapping rules for transformation
end

function from_dict(::Type{SensorFormatConfig}, dict::Dict{String, Any})::SensorFormatConfig
    columns = if haskey(dict, "columns")
        [from_dict(SensorColumnConfig, Dict{String, Any}(col)) for col in dict["columns"]]
    else
        SensorColumnConfig[]
    end
    
    mappings = if haskey(dict, "mappings")
        [from_dict(MappingRule, Dict{String, Any}(mapping)) for mapping in dict["mappings"]]
    else
        MappingRule[]
    end
    
    SensorFormatConfig(
        columns,
        dict["timestamp_column"],
        get(dict, "timestamp_format", nothing),
        get(dict, "delim", nothing),
        get(dict, "skip_to", nothing),
        mappings
    )
end

function to_dict(sfc::SensorFormatConfig)::Dict{String, Any}
    result = Dict{String, Any}(
        "columns" => [to_dict(col) for col in sfc.columns],
        "timestamp_column" => sfc.timestamp_column,
        "mappings" => [to_dict(mapping) for mapping in sfc.mappings]
    )
    
    if !isnothing(sfc.timestamp_format)
        result["timestamp_format"] = sfc.timestamp_format
    end
    if !isnothing(sfc.delim)
        result["delim"] = sfc.delim
    end
    if !isnothing(sfc.skip_to)
        result["skip_to"] = sfc.skip_to
    end
    
    result
end

"""
Configuration for time series interpolation
"""
struct InterpolationConfig
    from_minutes::Int                                # Source interval in minutes
    to_minutes::Int                                  # Target interval in minutes
end

function from_dict(::Type{InterpolationConfig}, dict::Dict{String, Any})::InterpolationConfig
    InterpolationConfig(
        dict["from_minutes"],
        dict["to_minutes"]
    )
end

function to_dict(ic::InterpolationConfig)::Dict{String, Any}
    Dict{String, Any}(
        "from_minutes" => ic.from_minutes,
        "to_minutes" => ic.to_minutes
    )
end

"""
Configuration for a single file in parse-sensors processing
"""
struct ParseSensorsFileConfig
    input::String                                    # Input file path
    name::Union{String, Nothing}                     # Optional name (defaults to basename)
    sensor::Union{String, SensorFormatConfig}        # Sensor config (file path or embedded)
    output::Union{TimeSeriesSource, Nothing}         # Output configuration
    interpolate::Union{InterpolationConfig, Nothing} # Optional interpolation configuration
end

function from_dict(::Type{ParseSensorsFileConfig}, dict::Dict{String, Any})::ParseSensorsFileConfig
    # Handle sensor as either string (file path) or embedded config
    sensor = if dict["sensor"] isa String
        dict["sensor"]
    else
        from_dict(SensorFormatConfig, Dict{String, Any}(dict["sensor"]))
    end

    output :: Union{TimeSeriesSource, Nothing} = if haskey(dict, "output") && !isnothing(dict["output"])
        from_dict(TimeSeriesSource, dict["output"])
    else
        nothing
    end

    interpolate :: Union{InterpolationConfig, Nothing} = if haskey(dict, "interpolate") && !isnothing(dict["interpolate"])
        from_dict(InterpolationConfig, Dict{String, Any}(dict["interpolate"]))
    else
        nothing
    end

    ParseSensorsFileConfig(
        dict["input"],
        get(dict, "name", nothing),
        sensor,
        output,
        interpolate
    )
end

function to_dict(psfc::ParseSensorsFileConfig)::Dict{String, Any}
    result = Dict{String, Any}(
        "input" => psfc.input,
        "output" => psfc.output isa TimeSeriesSource ? to_dict(psfc.output) : nothing
    )

    if !isnothing(psfc.name)
        result["name"] = psfc.name
    end

    if psfc.sensor isa String
        result["sensor"] = psfc.sensor
    else
        result["sensor"] = to_dict(psfc.sensor)
    end

    if !isnothing(psfc.interpolate)
        result["interpolate"] = to_dict(psfc.interpolate)
    end

    result
end

"""
Main configuration for parse-sensors.toml
"""
struct ParseSensorsConfiguration
    masts::Vector{ParseSensorsFileConfig}
    mesos::Vector{ParseSensorsFileConfig}
end

function from_dict(::Type{ParseSensorsConfiguration}, dict::Dict{String, Any})::ParseSensorsConfiguration
    masts = haskey(dict, "masts") ? [from_dict(ParseSensorsFileConfig, Dict{String, Any}(m)) for m in dict["masts"]] : []
    mesos = haskey(dict, "mesos") ? [from_dict(ParseSensorsFileConfig, Dict{String, Any}(m)) for m in dict["mesos"]] : []
    ParseSensorsConfiguration(masts, mesos)
end

function to_dict(psc::ParseSensorsConfiguration)::Dict{String, Any}
    Dict{String, Any}(
        "masts" => [to_dict(m) for m in psc.masts],
        "mesos" => [to_dict(m) for m in psc.mesos]
    )
end

export RuleOutcome, MappingRule, PatternConfig, SensorColumnConfig, SensorFormatConfig,
       ParseSensorsFileConfig, ParseSensorsConfiguration, InterpolationConfig,
       apply_mapping, matches_rule, merge_outcomes, safe_something

# --- Normalized Configuration Structs ---
# These structs hold the fully resolved and absolute-pathed configuration after loading.

struct ParseSensorsFileConfigNormalized
    input::String
    name::String
    sensor::SensorFormatConfig
    output::TimeSeriesSource
    interpolate::Union{InterpolationConfig, Nothing}
end

function from_dict(::Type{ParseSensorsFileConfigNormalized}, dict::Dict{String, Any})::ParseSensorsFileConfigNormalized
    sensor = from_dict(SensorFormatConfig, Dict{String, Any}(dict["sensor"]))
    output = from_dict(TimeSeriesSource, Dict{String, Any}(dict["output"]))

    interpolate = if haskey(dict, "interpolate") && !isnothing(dict["interpolate"])
        from_dict(InterpolationConfig, Dict{String, Any}(dict["interpolate"]))
    else
        nothing
    end

    ParseSensorsFileConfigNormalized(
        dict["input"],
        dict["name"],
        sensor,
        output,
        interpolate
    )
end

struct ParseSensorsConfigurationNormalized
    masts::Vector{ParseSensorsFileConfigNormalized}
    mesos::Vector{ParseSensorsFileConfigNormalized}
end

export ParseSensorsFileConfigNormalized, ParseSensorsConfigurationNormalized
       
end # end module 