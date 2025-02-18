module TimeRangeProcessor
using ...Types.MastTimeSeries: TimeSeriesData, TimeRange
using ...Types.CleanMastConfig: ConfigTimeRange
using Dates

"""
    calculate_reconstruction_time_range(ts::TimeSeriesData, time_range::Union{ConfigTimeRange,Nothing})::TimeRange

Calculate the time range for reconstruction of a time series for later analysis.
If no time range is provided, uses default of 1 year before the latest data point.

# Arguments
- `ts::TimeSeriesData`: Input time series data
- `time_range::Union{ConfigTimeRange,Nothing}`: Optional time range constraints

# Returns
- `TimeRange`: Calculated effective time range
"""
function calculate_reconstruction_time_range(mast_ts::TimeSeriesData, time_range::Union{ConfigTimeRange,Nothing})::TimeRange
    if isnothing(time_range)
        time_range = ConfigTimeRange(nothing, nothing)
    end
    
    # Get data bounds
    valid_times = filter(!ismissing, mast_ts.df.timestamp)
    data_max = maximum(valid_times)
    
    # Calculate default range (1 year before max date)
    default_min = floor(something(time_range.max, data_max) - Year(1), Month(1))
    
    # Determine actual min and max
    actual_min = something(time_range.min, default_min)
    actual_max = something(time_range.max, actual_min + Year(1))
    
    # If actual_max is at start of day, reduce by 1 second to avoid partial day
    if is_start_of_day(actual_max)
        actual_max -= Second(1)
    end
    
    TimeRange(actual_min, actual_max)
end

"""
    is_start_of_day(dt::DateTime)::Bool

Check if a DateTime is at the start of a day (00:00:00).

# Arguments
- `dt::DateTime`: DateTime to check

# Returns
- `Bool`: true if DateTime is at start of day
"""
function is_start_of_day(dt::DateTime)::Bool
    hour(dt) == 0 && minute(dt) == 0 && second(dt) == 0
end

export calculate_time_range
end