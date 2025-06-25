# src/CleanMastRules/ProcessRange.jl
"""
Range Rule Processing:
Validates if values fall within specified ranges. Each rule specifies:
- Sensor type (WindSpeed, WindDirection, Temperature)
- Optional height filter
- Min/max range values
Values outside the range are marked as violations.
Missing values are ignored.
"""

module ProcessRange

using DataFrames
using ...Types.CleanRules: Rule, RuleViolation, RangeCriteria
using ..ProcessTypes: filter_applicable_columns
using ...Types.MastTimeSeries: TimeSeriesData

function apply(rule::Rule, data::TimeSeriesData)::Vector{RuleViolation}
    @assert rule.criteria isa RangeCriteria
    columns = filter_applicable_columns(rule, data.sensors)
    criteria = rule.criteria
    
    violations = RuleViolation[]
    for col in columns
        violation_indices = Int[]
        if !isnothing(criteria.min)
            append!(violation_indices, findall(x -> !ismissing(x) && x < criteria.min, data.df[!, col]))
        end
        if !isnothing(criteria.max)
            append!(violation_indices, findall(x -> !ismissing(x) && x > criteria.max, data.df[!, col]))
        end
        unique_timestamps = sort(unique(data.df[unique(violation_indices), :timestamp]))
        append!(violations,  map(x -> RuleViolation(rule, x, col), unique_timestamps))
    end

    return violations
end

export apply
end
