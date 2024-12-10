# src/CleanMastRules/Process.jl
module Process

using DataFrames
using Dates
using ...Types.CleanRules
using ..ProcessTypes
using ..ProcessRange
using ..ProcessLayerDiff
using ..ProcessIcing
using ...Types.MastTimeSeries: SensorColumn, TimeSeriesData

function apply_rule(rule::Rule, data::TimeSeriesData)::Vector{RuleViolation}
    if rule.criteria isa RangeCriteria
        return ProcessRange.apply(rule, data)
    elseif rule.criteria isa LayerDifferenceCriteria
        return ProcessLayerDiff.apply(rule, data)
    else # IcingCriteria
        return ProcessIcing.apply(rule, data)
    end
end

"""
Sets cells in TimeSeriesData to missing according to violations
    
Parameters
----------
violations : Vector{RuleViolation}
    Vector of rule violations containing timestamp and column info
data : TimeSeriesData 
    Data to be modified in place

Returns
-------
Nothing
"""
function apply_missing!(violations::Vector{RuleViolation}, data::TimeSeriesData)::Nothing
    df = data.df
    
    # Group violations by column for fewer DataFrame operations
    by_column = Dict{Symbol, Vector{DateTime}}()
    for v in violations
        push!(get!(by_column, v.column, DateTime[]), v.timestamp)
    end

    symbols = Symbol.(names(df))
    
    # Set missing values column by column
    for (col, timestamps) in by_column
        if col in symbols
            df[in.(df.timestamp, Ref(timestamps)), col] .= missing
        else
            @warn "Column $col not found in DataFrame"
        end
    end
    
    return nothing
end

"""
Applies multiple rules sequentially to data, setting violating cells to missing after each rule
    
Parameters
----------
rules : Vector{Rule}
    Rules to apply in sequence
data : TimeSeriesData
    Data to be processed and modified in place
    
Returns
-------
Vector{RuleViolation}
    Collection of all violations found across all rules
"""
function apply_rules!(rules::Vector{Rule}, data::TimeSeriesData)::Vector{RuleViolation}
    all_violations = RuleViolation[]
    
    for rule in rules
        violations = apply_rule(rule, data)
        append!(all_violations, violations)
        apply_missing!(violations, data)
    end
    
    return all_violations
end

export apply_rule, apply_missing!

end # module

