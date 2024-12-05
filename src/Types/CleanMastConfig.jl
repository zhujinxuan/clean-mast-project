#src/Types/CleanMastConfig.jl
"""
Types for project config, corresponding to {project_dir}/config.yaml
"""
module CleanMastConfig
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

function parse_mapping_rules(mapping_dict::Dict) :: Vector{MapingRule}
    rules = MappingRule[]
    
    for mapping in mapping_dict
        match_dict = Dict{String, Union{Nothing, Float64, String}}()
        for (k, v) in mapping["match"]
            match_dict[k] = v isa Number ? convert(Float64, v) : v
        end
        
        rule_dict = mapping["rule"]
        rule_outcome = RuleOutcome(
            sensorType = get(rule_dict, "sensorType", nothing),
            sensorDirection = get(rule_dict, "sensorDirection", nothing),
            height = rule_dict["height"] isa Number ? convert(Float64, rule_dict["height"]) : nothing,
            statType = get(rule_dict, "statType", nothing),
            unit = get(rule_dict, "unit", nothing)
        )
        
        push!(rules, MappingRule(match_dict, rule_outcome))
    end
    
    return rules
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

struct MastConfig
  data_path::String
  skip_to::Union{Int, Vector{String}}
  sensor::SensorConfig
  rules::Vector{Rule}  # Using Rules.Rule
end

struct ProjectConfig
  mast::MastConfig
end

struct SensorMetadata
  columnName::String
  sensorType::String
  sensorDirection::String
  height::Float64
  statType::String
  unit::String
end

end # end module
