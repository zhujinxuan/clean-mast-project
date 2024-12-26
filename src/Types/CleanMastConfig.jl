#src/Types/CleanMastConfig.jl
"""
Types for project config, corresponding to {project_dir}/config.yaml
"""
module CleanMastConfig
using ..CleanRules
using ..Utils

struct RuleOutcome
    sensorType::Union{String, Nothing}
    sensorDirection::Union{String, Nothing}
    height::Union{Float64, Nothing}
    statType::Union{String, Nothing}
    unit::Union{String, Nothing}
end

# Constructor for RuleOutcome with optional fields
function RuleOutcome(;
    sensorType::Union{String, Nothing}=nothing,
    sensorDirection::Union{String, Nothing}=nothing,
    height::Union{Float64, Nothing}=nothing,
    statType::Union{String, Nothing}=nothing,
    unit::Union{String, Nothing}=nothing
)
    RuleOutcome(sensorType, sensorDirection, height, statType, unit)
end
export RuleOutcome

# Define a single mapping rule
struct MappingRule
    match::Dict{String, Union{Nothing, Float64, String}}
    rule::RuleOutcome
end
export MappingRule

# Constructor from dictionary for RuleOutcome
function from_dict(::Type{RuleOutcome}, dict::Dict{String, Any})::RuleOutcome
    RuleOutcome(
        get(dict, "sensorType", nothing),
        get(dict, "sensorDirection", nothing),
        get(dict, "height", nothing) |> h -> h isa Number ? convert(Float64, h) : nothing,
        get(dict, "statType", nothing),
        get(dict, "unit", nothing)
    )
end

function parse_mapping_rules(mapping_dict::Vector{Dict{String, Any}}) :: Vector{MappingRule}
    map(mapping_dict) do mapping
        match_dict = Dict{String, Union{Nothing, Float64, String}}(
            k => v isa Number ? convert(Float64, v) : v 
            for (k, v) in mapping["match"]
        )
        
        MappingRule(match_dict, from_dict(RuleOutcome, Dict{String, Any}(mapping["rule"])))
    end
end

export parse_mapping_rules

# Safe version of something that returns nothing if all args are nothing
safe_something(args...) = all(isnothing, args) ? nothing : something(args...)

# Functional merge for RuleOutcome
merge_outcomes(a::RuleOutcome, b::RuleOutcome)::RuleOutcome =
RuleOutcome(
            safe_something(b.sensorType, a.sensorType, nothing),
            safe_something(b.sensorDirection, a.sensorDirection, nothing),
            safe_something(b.height, a.height, nothing),
            safe_something(b.statType, a.statType, nothing),
            safe_something(b.unit, a.unit, nothing)
           )

# Functional rule matching
function matches_rule(rule::MappingRule, input::Dict{String, Any})::Bool
    all(((k,v),) -> get(input, k, nothing) == v, pairs(rule.match))
end

# Functional apply_mapping
function apply_mapping(rules::Vector{MappingRule}, input::Dict{String, Any})::RuleOutcome
  matching_rules = filter(rule -> matches_rule(rule, input), rules)
  isempty(matching_rules) && return RuleOutcome(nothing, nothing, nothing, nothing, nothing)

  reduce(merge_outcomes, map(rule -> rule.rule, matching_rules))
end


struct SensorConfig
  column_format::String
  timestamp_column::String
  timestamp_format::String
  mappings:: Vector{MappingRule}
end
export SensorConfig

struct MastConfig
  data_path::String
  skip_to::Union{Int, Vector{String}}
  delim::Union{Nothing, String}
  sensor::SensorConfig
  rules::Vector{Rule}  # Using Rules.Rule
end
export MastConfig

struct TimeRange
    min::Union{Nothing, DateTime}
    max::Union{Nothing, DateTime}
end

struct AnalysisConfig
    time_range::TimeRange
end

struct MesoConfig
    data_path::String
    delim::Union{Nothing, String}
    skip_to::Union{Int, Vector{String}}
    timestamp_column::Vector{String}
    timestamp_format::String
    sensor::SensorConfig
end

struct ProjectConfig
    mast::MastConfig
    meso::MesoConfig
    analysis::AnalysisConfig
end
export ProjectConfig

struct SensorMetadata
  columnName::String
  sensorType::String
  sensorDirection::String
  height::Float64
  statType::String
  unit::String
end
export SensorMetadata

function from_dict(::Type{TimeRange}, dict::Dict{String, Any})::TimeRange
    TimeRange(
        get(dict, "min", nothing),
        get(dict, "max", nothing)
    )
end

function from_dict(::Type{AnalysisConfig}, dict::Dict{String, Any})::AnalysisConfig
    AnalysisConfig(
        from_dict(TimeRange, dict["time_range"])
    )
end

function from_dict(::Type{MesoConfig}, dict::Dict{String, Any})::MesoConfig
    MesoConfig(
        dict["data_path"],
        get(dict, "delim", nothing),
        Vector{String}(dict["skip_to"]),
        Vector{String}(dict["timestamp_column"]),
        dict["timestamp_format"],
        from_dict(SensorConfig, Dict{String, Any}(dict["sensor"]))
    )
end

function to_dict(tr::TimeRange)::Dict
    Dict(
        "min" => tr.min,
        "max" => tr.max
    )
end

function to_dict(ac::AnalysisConfig)::Dict
    Dict(
        "time_range" => to_dict(ac.time_range)
    )
end

function to_dict(mc::MesoConfig)::Dict
    Dict(
        "data_path" => mc.data_path,
        "delim" => mc.delim,
        "skip_to" => mc.skip_to,
        "timestamp_column" => mc.timestamp_column,
        "timestamp_format" => mc.timestamp_format,
        "sensor" => to_dict(mc.sensor)
    )
end

function from_dict(::Type{SensorConfig}, dict::Dict{String, Any})::SensorConfig
    SensorConfig(
        dict["column_format"],
        dict["timestamp_column"],
        dict["timestamp_format"],
        parse_mapping_rules(dict["mappings"])
    )
end

export TimeRange, AnalysisConfig, MesoConfig

end # end module
