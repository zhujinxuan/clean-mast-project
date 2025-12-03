module ProcessCleanConfig

import ..Utils: from_dict
using ..MastTimeSeries: TimeSeriesSource
using ..CleanRules: Rule
using ...CleanMastUtils: load_dict

export Mast, ProcessCleanConfiguration, load_rules

struct Mast
    name::String
    input::TimeSeriesSource
    output::TimeSeriesSource
    rules::Union{String,Array}
end

struct ProcessCleanConfiguration
    masts::Vector{Mast}
end

function from_dict(::Type{ProcessCleanConfiguration}, dict::Dict{String, Any})
    masts = [from_dict(Mast, m) for m in dict["masts"]]
    return ProcessCleanConfiguration(masts)
end

function from_dict(::Type{Mast}, dict::Dict{String, Any})
    name = dict["name"]
    input = from_dict(TimeSeriesSource, dict["input"])
    output = from_dict(TimeSeriesSource, dict["output"])
    rules = dict["rules"]
    return Mast(name, input, output, rules)
end

"""
    load_rules(rules_config::Union{String, Array}, base_dir::String) -> Vector{Rule}

Load rules from either a file path (String) or inline configuration (Array).

# Arguments
- `rules_config`: Either a file path (String) to a rules file, or an inline rules Array
- `base_dir`: Base directory for resolving relative file paths

# Returns
- `Vector{Rule}`: Parsed rules

# Examples
```julia
# Load from file
rules = load_rules("rules/clean-rules.toml", "/path/to/project")

# Load from inline config
rules_config = [Dict("name" => "range_check", "type" => "range", ...)]
rules = load_rules(rules_config, ".")
```
"""
function load_rules(rules_config::Union{String, Array}, base_dir::String)::Vector{Rule}
    rules_dict = if isa(rules_config, String)
        load_dict(joinpath(base_dir, rules_config))
    else
        Dict("rules" => rules_config)
    end

    return [from_dict(Rule, r) for r in rules_dict["rules"]]
end

end 