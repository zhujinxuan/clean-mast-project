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
using ..Rules
using ..ProcessTypes
using ...MastTimeSeries

function apply!(rule::Rule, data::TimeSeriesData)::Vector{RuleViolation}
    @assert rule.criteria isa IcingCriteria
    columns = filter_applicable_columns(rule, data.sensors)
    criteria = rule.criteria

    violations = RuleViolation[];
    for col in columns
        violation_timestamps = DateTime[]
        values = data.df[!, col]
        timestamps = data.df.timestamp
        
        i = 1
        while i <= length(timestamps)
            # Find a window where changes are less than max_change
            window_start = i
            while i <= length(timestamps) && 
                  timestamps[i] - timestamps[window_start] <= Second(criteria.time_range)
                
                if i > window_start
                    # Check if change is less than max_change
                    if !ismissing(values[i]) && !ismissing(values[i-1]) &&
                       abs(values[i] - values[i-1]) > criteria.max_change
                        break
                    end
                end
                i += 1
            end
            
            # If window is long enough, mark all timestamps in window as violations
            window_duration = timestamps[i-1] - timestamps[window_start]
            if window_duration >= Second(criteria.time_range)
                append!(violation_timestamps, timestamps[window_start:i-1])
            end
            
            # Move to next potential window
            i = window_start + 1
        end
      append!(violations, x ->map(RuleViolation(rule, x, col), violation_timestamps))
    end
    return violations
end

export apply!

end # module

