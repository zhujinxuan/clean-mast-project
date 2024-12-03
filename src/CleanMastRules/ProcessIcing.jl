# src/CleanMastRules/ProcessIcing.jl
"""
Icing Rule Processing:
Detects potential icing conditions by identifying periods of minimal variation:
- Monitors value changes over specified time window (e.g. 7200 seconds)
- If changes remain below threshold (e.g. 0.02) for entire window, marks as icing
- Supports height-specific thresholds
- Handles gaps in data by restarting window check
"""
module ProcessIcing

using DataFrames
using Dates
using ...Types.CleanRules
using ..ProcessTypes
using ...MastTimeSeries

function apply(rule::Rule, data::TimeSeriesData)::Vector{RuleViolation}
    @assert rule.criteria isa IcingCriteria
    columns = filter_applicable_columns(rule, data.sensors)
    criteria = rule.criteria

    violations = RuleViolation[];
    for col in columns
        violation_timestamps = DateTime[]
        values = data.df[!, col]
        timestamps = data.df[!, :timestamp]
        
        window_start = 1
        while window_start <= length(timestamps)
            # Find a window where changes are less than max_change
            value_start = values[window_start]
            if (ismissing(value_start))
              window_start = window_start + 1
              continue 
            end

            window_end = window_start + 1
            while window_end <= length(timestamps)
                # Check if change is less than max_change
                value_end = values[window_end]
                if !ismissing(value_end) && abs(value_end - value_start) > criteria.max_change
                   break
                end
                window_end += 1
            end
            
            # If window is long enough, mark all timestamps in window as violations
            window_duration = timestamps[window_end-1] - timestamps[window_start]
            if window_duration >= Second(criteria.time_range)
                append!(violation_timestamps, timestamps[window_start:window_end-1])
            end
            
            # Move to next potential window
            window_start = window_end
        end
      append!(violations, map(x -> RuleViolation(rule, x, col), violation_timestamps))
    end
    return violations
end

export apply

end # module

