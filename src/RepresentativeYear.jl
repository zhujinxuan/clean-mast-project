module RepresentativeYear

using Dates
using DataFrames
using ..Types.MastTimeSeries: TimeSeriesData, TimeRange, SensorColumn
using ..Types.RepresentativeYear: CalibrationResults, DirectionalCalibration
using ..Types.SpeedReferenceModel.SectorizedRegression: SectorizedRegressionModel
using ..Types.SpeedReferenceModel.SectorizedRegression: find_pair_from_mast_sensor
using ..TimeSeriesProcessing.Interpolation: interpolate_timeseries

include("./RepresentativeYear/Analysis.jl")
using .Analysis

function find_heighest_meso_sensor(meso_ts::TimeSeriesData)::Union{SensorColumn, Nothing}
    # Filter sensors with statType = "avg" and sensorType = "WindSpeed"
    avg_wind_speed_sensors = filter(sensor -> sensor.statType == "avg" && sensor.sensorType == "WindSpeed", meso_ts.sensors)
    if isempty(avg_wind_speed_sensors)
        return nothing
    end
    foldl(avg_wind_speed_sensors, init=first(avg_wind_speed_sensors)) do max_sensor, sensor
        if (sensor.height > max_sensor.height)
            sensor
        else
            max_sensor
        end
    end
end

"""
Main function to perform representative year calibration
"""
function calibrate_to_representative_year(
    mast_ts::TimeSeriesData,
    meso_ts::TimeSeriesData,
    mast_time_range::TimeRange,
    sectorized_regression_model::SectorizedRegressionModel
)::Tuple{TimeSeriesData, Union{Nothing, CalibrationResults}}
    meso_sensor = find_heighest_meso_sensor(meso_ts)
    if (isnothing(meso_sensor))
        error("No suitable meso wind speed sensor found")
    end

    # Calculate mean speeds for meso sensor
    meso_full_mean = calculate_mean_speed(meso_ts, meso_sensor)
    
    # Filter DataFrame and create new TimeSeriesData for training range
    meso_training_df = filter(
        row -> mast_time_range.min <= row.timestamp <= mast_time_range.max, 
        meso_ts.df
    )
    meso_training_ts = TimeSeriesData(meso_training_df, meso_ts.sensors)
    meso_range_mean = calculate_mean_speed(meso_training_ts, meso_sensor)
    
    # Check if calibration is needed
    needs_calibration = is_calibration_needed(meso_full_mean, meso_range_mean)
    
    if !needs_calibration
        return (mast_ts, nothing)
    end
    
    # Find representative year start DateTime
    ref_year_start = find_representative_year(meso_ts, meso_full_mean, meso_sensor)
    

    # Calculate meso speed difference for this sector
    sector_meso_diff_df = calculate_sector_meso_diff(
        meso_ts,
        mast_time_range,
        ref_year_start,
        meso_sensor
    )

    # Use the pre-trained model's sectors and coefficients for calibration
    calibration_each_ws_sensors = map(sectorized_regression_model.pairs) do pair 
        calculate_calibration_each_ws_sensor(
            sector_meso_diff_df,
            pair
        )
    end
    
    # Create calibration results
    calibration = CalibrationResults(
        calibration_each_ws_sensors,
        ref_year_start,
    )

    meso_interpolated = interpolate_timeseries(meso_ts, mast_ts.df.timestamp)
    
    # Apply calibration
    ts = apply_calibration(mast_ts, calibration, meso_interpolated)
    return (ts, calibration)
end

export calibrate_to_representative_year

end 