# src/CleanMastRules/Process.jl
module Process

using DataFrames
using ..Rules
using ..ProcessTypes
using ..ProcessRange
using ...MastTimeSeries

function apply_rule(rule::Rule, data::TimeSeriesData)::Vector{RuleViolation}
    if rule.criteria isa RangeCriteria
        return ProcessRange.apply(rule, data)
    elseif rule.criteria isa LayerDifferenceCriteria
        return ProcessLayerDiff.apply(rule, data)
    else # IcingCriteria
        return ProcessIcing.apply(rule, data)
    end
end

export apply_rule

end # module

