#src/Types/CleanMastConfig.jl
"""
Types for project config, corresponding to {project_dir}/config.yaml
"""
module CleanMastConfig
using Dates
import ..Utils: from_dict, to_dict
using ..CleanRules: Rule
using ..ParseSensorsConfig: RuleOutcome, MappingRule, apply_mapping, matches_rule, merge_outcomes, safe_something

struct MastConfig
  name::String
end
export MastConfig

struct ConfigTimeRange
    min::Union{Nothing, DateTime}
    max::Union{Nothing, DateTime}
end

struct AnalysisConfig
    time_range::ConfigTimeRange
end

struct MesoConfig
    name::String
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
        from_dict(ConfigTimeRange, Dict{String, Any}(dict["time_range"]))
    )
end

function from_dict(::Type{MesoConfig}, dict::Dict{String, Any})::MesoConfig
    MesoConfig(
        dict["name"]
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
        "time_range" => to_dict(ac.time_range)
    )
end

function to_dict(mc::MesoConfig)::Dict{String, Any}
    Dict(
        "name" => mc.name
    )
end

function from_dict(::Type{MastConfig}, dict::Dict{String, Any})::MastConfig
    MastConfig(
        dict["name"]
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
