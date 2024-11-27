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
using ..Rules
using ..ProcessTypes
using ...MastTimeSeries

function apply(rule::Rule, data::TimeSeriesData)::RuleViolation
    @assert rule.criteria isa RangeCriteria
    columns = filter_applicable_columns(rule, data.sensors)
    criteria = rule.criteria
    
    violation_indices = Int[]
    for col in columns
        if !isnothing(criteria.min)
            append!(violation_indices, findall(x -> !ismissing(x) && x < criteria.min, data.df[!, col]))
        end
        if !isnothing(criteria.max)
            append!(violation_indices, findall(x -> !ismissing(x) && x > criteria.max, data.df[!, col]))
        end
    end
    
    unique_timestamps = sort(unique(data.df[unique(violation_indices), :timestamp]))
    return RuleViolation(rule, unique_timestamps, columns)
end

export apply
end
