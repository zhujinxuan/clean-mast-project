# src/CleanMastRules/ProcessTypes.jl
module ProcessTypes

using DataFrames
using Dates
using ..Rules
using ...MastTimeSeries

struct RuleViolation
    rule::Rule
    timestamp::DateTime
    column::Symbol
end

function filter_applicable_columns(rule::Rule, sensors::Vector{SensorColumn})::Vector{Symbol}
    return [s.columnName for s in sensors if 
        s.sensorType == rule.sensorType &&
        s.statType == "avg" &&
        (isnothing(rule.height.min) || s.height >= rule.height.min) &&
        (isnothing(rule.height.max) || s.height <= rule.height.max)]
end

function apply_missing!(violations::Vector{RuleViolation}, data::TimeSeriesData)::Nothing
    df = data.df
    
    # Group violations by timestamp to reduce number of operations
    for violation in violations
        # Use logical indexing to find matching rows
        matching_rows = df.timestamp .== violation.timestamp
        
        # Convert column name to symbol and check if it exists
        col_sym = violation.column
        if col_sym in names(df)
            # Set matching cells to missing
            df[matching_rows, col_sym] .= missing
        else
            @warn "Warning: Column $(violation.column) not found in DataFrame."
        end
    end
    
    return nothing
end


export RuleViolation, filter_applicable_columns, apply_missing!

end # module

