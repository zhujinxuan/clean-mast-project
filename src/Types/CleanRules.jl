# src/Types/CleanRules.jl
"""
Type definition for data cleaning
"""
module CleanRules

using DataFrames
using Dates
using ..MastTimeSeries: SensorColumn
import ..Utils: from_dict

struct HeightFilter
    min::Union{Nothing, Float64}
    max::Union{Nothing, Float64}
end

struct RangeCriteria
    min::Union{Nothing, Float64}
    max::Union{Nothing, Float64}
end

struct LayerDifferenceCriteria
    lower_layer_height::Float64
    abs_diff::RangeCriteria
    lower_wind_speed::RangeCriteria
end

struct IcingCriteria
    time_range::Int64
    max_change::Float64
end

struct ManualCriteria
end

struct Rule
    name::String
    sensorType::String
    height::HeightFilter
    criteria::Union{RangeCriteria, LayerDifferenceCriteria, IcingCriteria, ManualCriteria}
end

function from_dict(::Type{Rule}, config::Dict{String, Any})::Rule
    # Validate one and only one criteria type exists
    criteria_keys = ["out_of_range", "layer_difference", "icing"]
    present_keys = filter(k -> haskey(config, k), criteria_keys)
    
    if length(present_keys) != 1
        error("Rule must have exactly one of: $(join(criteria_keys, ", ")). Found: $(join(present_keys, ", "))")
    end

    height = HeightFilter(
        get(get(config, "height", Dict()), "min", nothing),
        get(get(config, "height", Dict()), "max", nothing)
    )

    if haskey(config, "out_of_range")
        criteria = RangeCriteria(
            get(config["out_of_range"], "min", nothing),
            get(config["out_of_range"], "max", nothing)
        )
    elseif haskey(config, "layer_difference")
        ld = config["layer_difference"]
        criteria = LayerDifferenceCriteria(
            ld["lower_layer_height"],
            RangeCriteria(
                get(ld["abs_diff"], "min", nothing),
                get(ld["abs_diff"], "max", nothing)
            ),
            RangeCriteria(
                get(ld["lower_wind_speed"], "min", nothing),
                get(ld["lower_wind_speed"], "max", nothing)
            )
        )
    else # must be icing based on validation above
        criteria = IcingCriteria(
            config["icing"]["time_range"],
            config["icing"]["max_change"]
        )
    end

    return Rule(
        config["name"],
        config["sensorType"],
        height,
        criteria
    )
end

struct RuleViolation
    rule::Rule
    timestamp::DateTime
    column::Symbol
end

export RuleViolation

export HeightFilter, RangeCriteria, LayerDifferenceCriteria, IcingCriteria, ManualCriteria,
       Rule, parse_rule

end # module

