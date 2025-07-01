module TimeRangeProcessor
using ...Types.MastTimeSeries: TimeSeriesData, TimeRange
using Dates

"""
    calculate_measurement_year_time_range(mast_ts::TimeSeriesData)::TimeRange

Calculate the time range for representative year calibration.
Uses the last year of available data.
TODO: I need to add test in future.

# Arguments
- `mast_ts::TimeSeriesData`: Input time series data

# Returns
- `TimeRange`: Calculated time range for representative year (last year of data)
"""
function calculate_measurement_year_time_range(mast_ts::TimeSeriesData)::TimeRange
    # Get data bounds
    valid_times = filter(!ismissing, mast_ts.df.timestamp)
    data_min = minimum(valid_times)
    data_max = maximum(valid_times)
    
    # Calculate default range (1 year before max date)
    from_max_min = floor(data_max - Month(11), Month(1))
    min1 = ceil(data_min, Month(1))
    
    # Ensure we don't go before data_min
    actual_min = min(from_max_min, min1)
    actual_max = actual_min + Year(1) - Second(1)
    
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

export calculate_measurement_year_time_range
end