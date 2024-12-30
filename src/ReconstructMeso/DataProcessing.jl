module DataProcessing

using DataFrames
using Statistics
using Dates
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.ReconstructMeso: TrainingTimeRange
using ...Types.CleanMastConfig: TimeRange
"""
Ensure TimeSeriesData has all timestamps in range at specified interval
"""
function ensure_complete_timeseries(ts::TimeSeriesData, time_range::TrainingTimeRange, 
                                  interval::Period)::TimeSeriesData
    start_time = time_range.min
    end_time = time_range.max
    
    # Create complete timestamp sequence
    complete_timestamps = collect(start_time:interval:end_time)
    
    # Create new DataFrame with complete timestamps and initialize with Union{Missing, Float64}
    new_df = DataFrame(timestamp = complete_timestamps)
    
    # Add sensor columns with missing values, ensuring proper type
    for sensor in ts.sensors
        new_df[!, sensor.columnName] = Vector{Union{Missing, Float64}}(missing, length(complete_timestamps))
    end
    
    # Fill in existing values
    matching_timestamps = map(t -> t ∈ ts.df.timestamp, complete_timestamps)
    matching_indices = indexin(complete_timestamps[matching_timestamps], ts.df.timestamp)
    sensor_columns = [s.columnName for s in ts.sensors]
    
    new_df[matching_timestamps, sensor_columns] = ts.df[matching_indices, sensor_columns]
    
    TimeSeriesData(new_df, ts.sensors)
end

"""
Prepare time series data by ensuring complete timestamps at specified interval
"""
function prepare_timeseries(ts::TimeSeriesData, time_range::TrainingTimeRange, 
                          interval::Minute)::TimeSeriesData
    # First ensure we have data for the full time range at specified interval
    complete_ts = ensure_complete_timeseries(ts, time_range, interval)
    
    # Sort by timestamp to ensure proper ordering
    sort!(complete_ts.df, :timestamp)
    
    complete_ts
end

"""
Average data over 15-day periods within time_range, marking periods with >30% missing data as missing.
The last period is marked as missing if it covers less than 2/3 of period_days.
"""
function average_timeseries(ts::TimeSeriesData, time_range::TrainingTimeRange, period_days::Int) :: TimeSeriesData
    # Filter data within time range
    filtered_df = filter(row -> time_range.min <= row.timestamp, ts.df)
    
    # Create period start timestamps
    period_starts = collect(time_range.min:Day(period_days):time_range.max)
    result_df = DataFrame(timestamp = period_starts)
    
    for sensor in ts.sensors
        # Initialize result column with missing values
        result_df[!, sensor.columnName] = Vector{Union{Missing, Float64}}(missing, length(period_starts))
    end

    last_ts = maximum(filtered_df.timestamp)
    # For each period
    for (i, period_start) in enumerate(period_starts)
        period_end = period_start + Day(period_days)
        
        # Get values for this period
        period_df = filter(row -> 
            period_start <= row.timestamp < period_end, 
            filtered_df)
        
        # For the last period, check if we have enough days
        if i == length(period_starts)
            days_in_period = (last_ts - period_start).value / (1000 * 60 * 60 * 24)  # Convert ms to days
            if days_in_period < 2/3 * period_days
                continue  # Skip processing, leaving it as missing
            end
        end
        
        # Only compute average if we have enough non-missing values (>70%)
        for sensor in ts.sensors
            period_values = period_df[!, sensor.columnName]
            non_missing = count(!ismissing, period_values)
            if !isempty(period_values) && non_missing > 0.7 * length(period_values)
                result_df[i, sensor.columnName] = mean(skipmissing(period_values))
            end
        end
    end
    
    TimeSeriesData(result_df, ts.sensors)
end

"""
Find nearest height sensor of specified type in sensors list
"""
function find_nearest_height_sensor(target_height::Float64, sensors::Vector{SensorColumn}, 
                                  sensor_type::String, stat_type::String="avg")::Union{SensorColumn, Nothing}
    matching_sensors = filter(s -> s.sensorType == sensor_type && s.statType == stat_type, sensors)
    isempty(matching_sensors) && return nothing
    
    # Find sensor with closest height
    closest_sensor = reduce((s1, s2) -> 
        abs(s1.height - target_height) < abs(s2.height - target_height) ? s1 : s2, 
        matching_sensors)
    
    return closest_sensor
end

"""
Calculate training time range from mast time series and optional time range input
"""
function calculate_training_timerange(ts::TimeSeriesData, time_range::Union{TimeRange,Nothing}) :: TrainingTimeRange
    if isnothing(time_range)
        time_range = TimeRange(nothing, nothing)
    end
    
    # Get data bounds
    data_max = maximum(ts.df.timestamp)
    
    # Calculate default range (1 year before max date)
    default_min = something(time_range.max, data_max) - Year(1)
    
    # Determine actual min and max
    actual_min = something(time_range.min, default_min)
    actual_max = something(time_range.max, actual_min + Year(1))
    
    TrainingTimeRange(actual_min, actual_max)
end

export average_timeseries, find_nearest_height_sensor, prepare_timeseries, calculate_training_timerange

end 