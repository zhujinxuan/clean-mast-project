module DataProcessing

using DataFrames
using Statistics
using Dates
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.CleanMastConfig: TimeRange

"""
Ensure TimeSeriesData has all timestamps in range at specified interval
"""
function ensure_complete_timeseries(ts::TimeSeriesData, time_range::TimeRange, 
                                  interval::Minute=Minute(10))::TimeSeriesData
    start_time = something(time_range.min, minimum(ts.df.timestamp))
    end_time = something(time_range.max, maximum(ts.df.timestamp))
    
    # Generate complete timestamp sequence
    all_timestamps = start_time:interval:end_time
    
    # Create DataFrame with all timestamps
    complete_df = DataFrame(timestamp = collect(all_timestamps))
    
    # Join with existing data
    result_df = leftjoin(complete_df, ts.df, on=:timestamp)
    
    TimeSeriesData(result_df, ts.sensors)
end

"""
Prepare time series data by ensuring complete timestamps at specified interval
"""
function prepare_timeseries(ts::TimeSeriesData, time_range::TimeRange, 
                          interval::Minute)::TimeSeriesData
    # First ensure we have data for the full time range at specified interval
    complete_ts = ensure_complete_timeseries(ts, time_range, interval)
    
    # Sort by timestamp to ensure proper ordering
    sort!(complete_ts.df, :timestamp)
    
    complete_ts
end

"""
Average data over 15-day periods within time_range, marking periods with >30% missing data as missing
"""
function average_timeseries(ts::TimeSeriesData, time_range::TimeRange, period_days::Int=15)::TimeSeriesData
    # First ensure complete timeseries at appropriate interval
    interval = ts.sensors[1].sensorType == "WindSpeed" ? Minute(10) : Minute(60)
    prepared_ts = prepare_timeseries(ts, time_range, interval)
    
    start_time = something(time_range.min, minimum(prepared_ts.df.timestamp))
    end_time = something(time_range.max, maximum(prepared_ts.df.timestamp))
    
    # Calculate periods relative to start_time
    prepared_ts.df[!, :period] = floor.(Int, (prepared_ts.df.timestamp .- start_time) / Day(period_days))
    
    # Calculate averages for each sensor in each period
    sensor_cols = [s.columnName for s in ts.sensors]
    
    period_averages = combine(groupby(prepared_ts.df, :period)) do group
        # For each sensor column
        result = Dict{Symbol, Union{Float64, Missing}}()
        for col in sensor_cols
            values = group[!, col]
            # If more than 30% missing, return missing
            if mean(ismissing.(values)) > 0.3
                result[col] = missing
            else
                result[col] = mean(skipmissing(values))
            end
        end
        # Add timestamp as middle of period
        period_start = start_time + Day(period_days * first(group.period))
        result[:timestamp] = period_start + Day(period_days ÷ 2)
        result
    end
    
    TimeSeriesData(period_averages, ts.sensors)
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

export average_timeseries, find_nearest_height_sensor, prepare_timeseries

end 