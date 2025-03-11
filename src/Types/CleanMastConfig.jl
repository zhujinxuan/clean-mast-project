#src/Types/CleanMastConfig.jl
"""
Types for project config, corresponding to {project_dir}/config.yaml
"""
module CleanMastConfig
using Dates
import ..Utils: from_dict, to_dict
using ..CleanRules: Rule

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

export RuleOutcome

# Define a single mapping rule
struct MappingRule
    match::Dict{String, Union{Nothing, Float64, String}}
    rule::RuleOutcome
end
export MappingRule

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

struct SensorConfig
    column_formats::Vector{String}  # Multiple format patterns
    timestamp_column::String
    timestamp_format::Union{String, Nothing}
    delim::Union{String, Nothing}
    skip_to::Union{Int64, Nothing}    # Modified to only accept Int or Nothing
    mappings::Vector{MappingRule}
end
export SensorConfig

struct MastConfig
  data_path::String
  sensor::Union{String, SensorConfig}
  rules::Vector{Rule}  
end
export MastConfig

struct ConfigTimeRange
    min::Union{Nothing, DateTime}
    max::Union{Nothing, DateTime}
end

struct AnalysisConfig
    time_range::ConfigTimeRange
    target_height::Union{Nothing, Float64}
    ti_target_height::Union{Nothing, Float64}
end

struct MesoConfig
    data_path::String
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
            DateTime(value, dateformat"yyyy-mm-dd")
        else  # Format: "2024-11-20 23:59:59"
            DateTime(value, dateformat"yyyy-mm-dd HH:MM:SS")
        end
    catch
        nothing
    end
end

function from_dict(::Type{ConfigTimeRange}, dict::Dict{String, Any})::ConfigTimeRange
    ConfigTimeRange(
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
        from_dict(ConfigTimeRange, Dict{String, Any}(dict["time_range"])),
        get(dict, "target_height", nothing) |> h -> h isa Number ? convert(Float64, h) : nothing,
        get(dict, "ti_target_height", nothing) |> h -> h isa Number ? convert(Float64, h) : nothing
    )
end

function from_dict(::Type{MesoConfig}, dict::Dict{String, Any})::MesoConfig
    MesoConfig(
        dict["data_path"],
        from_dict(SensorConfig, Dict{String, Any}(dict["sensor"]))
    )
end

function to_dict(tr::ConfigTimeRange)::Dict{String, Any}
    Dict(
        "min" => tr.min isa DateTime ? Dates.format(tr.min, "yyyy-mm-dd HH:MM:SS") : tr.min,
        "max" => tr.max isa DateTime ? Dates.format(tr.max, "yyyy-mm-dd HH:MM:SS") : tr.max
    )
end

function to_dict(ac::AnalysisConfig)::Dict{String, Any}
    Dict(
        "time_range" => to_dict(ac.time_range),
        "target_height" => ac.target_height,
        "ti_target_height" => ac.ti_target_height
    )
end

function to_dict(sc::SensorConfig)::Dict{String, Any}
    Dict{String, Any}(
        "column_formats" => sc.column_formats,
        "timestamp_column" => sc.timestamp_column,
        "timestamp_format" => sc.timestamp_format,
        "delim" => sc.delim,
        "skip_to" => sc.skip_to,
        "mappings" => map(to_dict, sc.mappings)
    )
end

function to_dict(mc::MesoConfig)::Dict{String, Any}
    Dict(
        "data_path" => mc.data_path,
        "sensor" => to_dict(mc.sensor)
    )
end

function from_dict(::Type{SensorConfig}, d::Dict{String, Any})::SensorConfig
    # Support both single format (backward compatibility) and multiple formats
    formats = if haskey(d, "column_formats")
        d["column_formats"]
    elseif haskey(d, "column_format")
        [d["column_format"]]
    else
        error("Either column_format or column_formats must be specified")
    end

    mappings = map(m -> from_dict(MappingRule, Dict{String, Any}(m)), d["mappings"])
    
    SensorConfig(
        formats,
        d["timestamp_column"],
        get(d, "timestamp_format", nothing),
        get(d, "delim", nothing),
        get(d, "skip_to", nothing),
        mappings
    )
end

function from_dict(::Type{MastConfig}, dict::Dict{String, Any})::MastConfig
    MastConfig(
        dict["data_path"],
        from_dict(SensorConfig, Dict{String, Any}(dict["sensor"])),
        haskey(dict, "rules") ? [from_dict(Rule, rule) for rule in dict["rules"]] : []
    )
end

function from_dict(::Type{ProjectConfig}, dict::Dict{String, Any})::ProjectConfig
    ProjectConfig(
        from_dict(MastConfig, Dict{String, Any}(dict["Mast"])),
        from_dict(MesoConfig, Dict{String, Any}(dict["Meso"])),
        from_dict(AnalysisConfig, Dict{String, Any}(dict["Analysis"]))
    )
end

export ConfigTimeRange, AnalysisConfig, MesoConfig

end # end module
