module Training

using DataFrames
using Statistics
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.ReconstructMeso: WindSpeedTrainResult, WindDirectionTrainResult,
                               WindSpeedTrainResults, WindDirectionTrainResults
using ..DataProcessing: find_nearest_height_sensor, average_timeseries

"""
Train wind speed correlation between mast and meso data using 15-day averages
"""
function train_wind_speed(avg_mast_ts::TimeSeriesData, avg_meso_ts::TimeSeriesData, 
                         min_height::Float64=50.0)::WindSpeedTrainResults
    # Filter mast sensors above minimum height
    mast_sensors = filter(s -> s.height >= min_height && s.sensorType == "WindSpeed" && 
                             s.statType == "avg", avg_mast_ts.sensors)
    
    # Create pairs of (mast_sensor, meso_sensor)
    sensor_pairs = filter(pair -> !isnothing(pair[2]),
        map(mast_sensor -> (
            mast_sensor,
            find_nearest_height_sensor(mast_sensor.height, avg_meso_ts.sensors, "WindSpeed", "avg")
        ), mast_sensors)
    )
    
    # Process each valid sensor pair and create results dictionary
    Dict(
        pair[1].columnName => result
        for pair in sensor_pairs
        for result in [process_windspeed_sensor_pair(pair[1], pair[2], avg_mast_ts, avg_meso_ts)]
        if !isnothing(result)
    )
end

function process_windspeed_sensor_pair(mast_sensor::SensorColumn, meso_sensor::SensorColumn,
                           avg_mast_ts::TimeSeriesData, avg_meso_ts::TimeSeriesData
                           )::Union{WindSpeedTrainResult, Nothing}
    # Get paired values
    paired_values = collect(zip(
        avg_mast_ts.df[!, mast_sensor.columnName],
        avg_meso_ts.df[!, meso_sensor.columnName]
    ))
    
    # Filter out missing values and unzip
    valid_pairs = filter(pair -> !ismissing(pair[1]) && !ismissing(pair[2]), paired_values)
    length(valid_pairs) < 10 && return nothing
    
    y, x = map(i -> Float64[p[i] for p in valid_pairs], (1, 2))
    
    # Calculate regression parameters
    slope = cov(x, y) / var(x)
    intercept = mean(y) - slope * mean(x)
    
    WindSpeedTrainResult(mast_sensor, meso_sensor, slope, intercept)
end

"""
Train wind direction offset between mast and meso data using 15-day averages
"""
function train_wind_direction(avg_mast_ts::TimeSeriesData, avg_meso_ts::TimeSeriesData, 
                            min_height::Float64=50.0)::WindDirectionTrainResults
    # Filter mast sensors above minimum height
    mast_sensors = filter(s -> s.height >= min_height && s.sensorType == "WindDirection" && 
                             s.statType == "avg", avg_mast_ts.sensors)
    
    # Create pairs of (mast_sensor, meso_sensor)
    sensor_pairs = filter(pair -> !isnothing(pair[2]),
        map(mast_sensor -> (
            mast_sensor,
            find_nearest_height_sensor(mast_sensor.height, avg_meso_ts.sensors, "WindDirection", "avg")
        ), mast_sensors)
    )
    
    # Process each valid sensor pair and create results dictionary
    Dict(
        pair[1].columnName => result
        for pair in sensor_pairs
        for result in [process_winddirection_sensor_pair(pair[1], pair[2], avg_mast_ts, avg_meso_ts)]
        if !isnothing(result)
    )
end

function process_winddirection_sensor_pair(mast_sensor::SensorColumn, meso_sensor::SensorColumn,
                                         avg_mast_ts::TimeSeriesData, avg_meso_ts::TimeSeriesData
                                         )::Union{WindDirectionTrainResult, Nothing}
    # Get paired values
    paired_values = collect(zip(
        avg_mast_ts.df[!, mast_sensor.columnName],
        avg_meso_ts.df[!, meso_sensor.columnName]
    ))
    
    # Filter out missing values
    valid_pairs = filter(pair -> !ismissing(pair[1]) && !ismissing(pair[2]), paired_values)
    length(valid_pairs) < 10 && return nothing
    
    # Unzip the filtered pairs
    mast_filtered, meso_filtered = map(i -> Float64[p[i] for p in valid_pairs], (1, 2))
    
    # Calculate direction differences
    diffs = @. mod((mast_filtered - meso_filtered + 180), 360) - 180
    mean_diff = mean(diffs)
    
    WindDirectionTrainResult(mast_sensor, meso_sensor, mean_diff)
end

export train_wind_speed, train_wind_direction

end 