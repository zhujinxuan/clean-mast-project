module Training

using DataFrames
using Statistics
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.ReconstructMeso: WindSpeedTrainResult, WindDirectionTrainResult,
                               WindSpeedTrainResults, WindDirectionTrainResults
using ..DataProcessing: find_nearest_height_sensor

"""
Train wind speed correlation between mast and meso data
"""
function train_wind_speed(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData, 
                         min_height::Float64=50.0)::WindSpeedTrainResults
    # Filter mast sensors above minimum height
    mast_sensors = filter(s -> s.height >= min_height && s.sensorType == "WindSpeed" && 
                             s.statType == "avg", mast_ts.sensors)
    
    results = Dict{Symbol, WindSpeedTrainResult}()
    
    for mast_sensor in mast_sensors
        # Find nearest meso sensor
        meso_sensor = find_nearest_height_sensor(mast_sensor.height, meso_ts.sensors, 
                                               "WindSpeed", "avg")
        isnothing(meso_sensor) && continue
        
        # Get paired data points (excluding missing values)
        paired_data = filter(row -> !ismissing(row[mast_sensor.columnName]) && 
                                  !ismissing(row[meso_sensor.columnName]), mast_ts.df)
        
        # Need minimum number of points for regression
        nrow(paired_data) < 10 && continue
        
        # Simple linear regression
        x = paired_data[!, meso_sensor.columnName]
        y = paired_data[!, mast_sensor.columnName]
        
        # y = mx + b
        slope = cov(x, y) / var(x)
        intercept = mean(y) - slope * mean(x)
        
        results[mast_sensor.columnName] = WindSpeedTrainResult(
            mast_sensor, meso_sensor, slope, intercept
        )
    end
    
    return results
end

"""
Train wind direction offset between mast and meso data
"""
function train_wind_direction(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData, 
                            min_height::Float64=50.0)::WindDirectionTrainResults
    # Filter mast sensors above minimum height
    mast_sensors = filter(s -> s.height >= min_height && s.sensorType == "WindDirection" && 
                             s.statType == "avg", mast_ts.sensors)
    
    results = Dict{Symbol, WindDirectionTrainResult}()
    
    for mast_sensor in mast_sensors
        # Find nearest meso sensor
        meso_sensor = find_nearest_height_sensor(mast_sensor.height, meso_ts.sensors, 
                                               "WindDirection", "avg")
        isnothing(meso_sensor) && continue
        
        # Get paired data points (excluding missing values)
        paired_data = filter(row -> !ismissing(row[mast_sensor.columnName]) && 
                                  !ismissing(row[meso_sensor.columnName]), mast_ts.df)
        
        # Need minimum number of points
        nrow(paired_data) < 10 && continue
        
        # Calculate mean direction difference (accounting for circular nature)
        diffs = @. mod((paired_data[!, mast_sensor.columnName] - 
                       paired_data[!, meso_sensor.columnName] + 180), 360) - 180
        mean_diff = mean(diffs)
        
        results[mast_sensor.columnName] = WindDirectionTrainResult(
            mast_sensor, meso_sensor, mean_diff
        )
    end
    
    return results
end

export train_wind_speed, train_wind_direction

end 