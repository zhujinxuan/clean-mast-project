#src/Types/CleanMastConfig.jl
"""
Types for project config, corresponding to {project_dir}/config.yaml
"""
module CleanMastConfig
using Dates
import ..Utils: from_dict, to_dict
using ..CleanRules

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
    target_height::Union{Nothing, Float64}
    ti_target_height::Union{Nothing, Float64}
end

struct MesoConfig
    data_path::String
    skip_to::Union{Int, Vector{String}}
    delim::Union{Nothing, String}
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

function parse_datetime(value::String)::Union{DateTime, Nothing}
    try
        if length(value) <= 10  # Format: "2024-11-20"
            DateTime(Date(value))
        else  # Format: "2024-11-20 23:59:59"
            DateTime(value, dateformat"yyyy-mm-dd HH:MM:SS")
        end
    catch
        nothing
    end
end

function from_dict(::Type{TimeRange}, dict::Dict{String, Any})::TimeRange
    TimeRange(
        let min_val = get(dict, "min", nothing)
            min_val isa String ? parse_datetime(min_val) : min_val
        end,
        let max_val = get(dict, "max", nothing)
            max_val isa String ? parse_datetime(max_val) : max_val
        end
    )
end

function from_dict(::Type{AnalysisConfig}, dict::Dict{String, Any})::AnalysisConfig
    AnalysisConfig(
        from_dict(TimeRange, Dict{String, Any}(dict["time_range"])),
        get(dict, "target_height", nothing) |> h -> h isa Number ? convert(Float64, h) : nothing,
        get(dict, "ti_target_height", nothing) |> h -> h isa Number ? convert(Float64, h) : nothing
    )
end

function from_dict(::Type{MesoConfig}, dict::Dict{String, Any})::MesoConfig
    MesoConfig(
        dict["data_path"],
        Vector{String}(dict["skip_to"]),
        get(dict, "delim", nothing),
        from_dict(SensorConfig, Dict{String, Any}(dict["sensor"]))
    )
end

function to_dict(tr::TimeRange)::Dict{String, Any}
    Dict(
        "min" => tr.min,
        "max" => tr.max
    )
end

function to_dict(ac::AnalysisConfig)::Dict{String, Any}
    Dict(
        "time_range" => to_dict(ac.time_range),
        "target_height" => ac.target_height,
        "ti_target_height" => ac.ti_target_height
    )
end

function to_dict(mc::MesoConfig)::Dict{String, Any}
    Dict(
        "data_path" => mc.data_path,
        "delim" => mc.delim,
        "skip_to" => mc.skip_to,
        "sensor" => to_dict(mc.sensor)
    )
end

function from_dict(::Type{SensorConfig}, dict::Dict{String, Any})::SensorConfig
    SensorConfig(
        dict["column_format"],
        dict["timestamp_column"],
        dict["timestamp_format"],
        parse_mapping_rules(Vector{Dict{String, Any}}(dict["mappings"]))
    )
end

function from_dict(::Type{MastConfig}, dict::Dict{String, Any})::MastConfig
    MastConfig(
        dict["data_path"],
        dict["skip_to"],
        get(dict, "delim", nothing),
        from_dict(SensorConfig, Dict{String, Any}(dict["sensor"])),
        haskey(dict, "rules") ? [parse_rule(rule) for rule in dict["rules"]] : Rule[]
    )
end

function from_dict(::Type{ProjectConfig}, dict::Dict{String, Any})::ProjectConfig
    ProjectConfig(
        from_dict(MastConfig, Dict{String, Any}(dict["Mast"])),
        from_dict(MesoConfig, Dict{String, Any}(dict["Meso"])),
        from_dict(AnalysisConfig, Dict{String, Any}(dict["Analysis"]))
    )
end

export TimeRange, AnalysisConfig, MesoConfig

end # end module
