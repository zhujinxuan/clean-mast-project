module PeriodOperations

using Dates

export TimePeriod, periods_overlap, compute_intersection, merge_consecutive_periods, calculate_duration_points

"""
    TimePeriod

Represents a time period with start and end times.

# Fields
- `start_time::DateTime`: Period start time
- `end_time::DateTime`: Period end time
- `duration_points::Int`: Number of data points in this period
"""
struct TimePeriod
    start_time::DateTime
    end_time::DateTime
    duration_points::Int
end

"""
    periods_overlap(p1::TimePeriod, p2::TimePeriod)::Bool

Check if two periods overlap in time.

# Arguments
- `p1::TimePeriod`: First period
- `p2::TimePeriod`: Second period

# Returns
- `Bool`: true if periods overlap, false otherwise
"""
function periods_overlap(p1::TimePeriod, p2::TimePeriod)::Bool
    return p1.start_time <= p2.end_time && p2.start_time <= p1.end_time
end

"""
    compute_intersection(p1::TimePeriod, p2::TimePeriod, p3::TimePeriod)::TimePeriod

Compute intersection of three periods.

# Arguments
- `p1::TimePeriod`: First period
- `p2::TimePeriod`: Second period
- `p3::TimePeriod`: Third period

# Returns
- `TimePeriod`: Intersection period (latest start to earliest end)
"""
function compute_intersection(p1::TimePeriod, p2::TimePeriod, p3::TimePeriod)::TimePeriod
    start_time = max(p1.start_time, p2.start_time, p3.start_time)
    end_time = min(p1.end_time, p2.end_time, p3.end_time)
    # Duration points will be recalculated later based on actual timestamps
    return TimePeriod(start_time, end_time, 0)  # Duration placeholder
end

"""
    merge_consecutive_periods(periods::Vector{TimePeriod}, rep_interval::Period)::Vector{TimePeriod}

Merge consecutive or overlapping periods.
Periods are consecutive if end_time1 + rep_interval >= start_time2.

# Arguments
- `periods::Vector{TimePeriod}`: List of periods to merge
- `rep_interval::Period`: Representative time interval (e.g., Minute(10))

# Returns
- `Vector{TimePeriod}`: Merged periods
"""
function merge_consecutive_periods(
    periods::Vector{TimePeriod},
    rep_interval::Period
)::Vector{TimePeriod}

    isempty(periods) && return periods

    # Sort by start time
    sorted = sort(periods, by = p -> p.start_time)

    merged = TimePeriod[]
    current = sorted[1]

    for i in 2:length(sorted)
        next_period = sorted[i]

        # Check if consecutive: end + interval >= next_start
        if current.end_time + rep_interval >= next_period.start_time
            # Merge - extend to later end time
            new_end = max(current.end_time, next_period.end_time)
            current = TimePeriod(
                current.start_time,
                new_end,
                current.duration_points + next_period.duration_points  # Sum points
            )
        else
            # Not consecutive - save current and start new
            push!(merged, current)
            current = next_period
        end
    end

    push!(merged, current)  # Don't forget the last one
    return merged
end

"""
    calculate_duration_points(start_time::DateTime, end_time::DateTime, rep_interval::Period)::Int

Calculate number of data points in a period based on time range and interval.

# Arguments
- `start_time::DateTime`: Period start
- `end_time::DateTime`: Period end
- `rep_interval::Period`: Data interval

# Returns
- `Int`: Approximate number of points (duration / interval)
"""
function calculate_duration_points(start_time::DateTime, end_time::DateTime, rep_interval::Period)::Int
    duration = end_time - start_time
    interval_ms = Dates.value(Millisecond(rep_interval))
    duration_ms = Dates.value(Millisecond(duration))
    return Int(ceil(duration_ms / interval_ms)) + 1  # +1 to include both endpoints
end

end # module
