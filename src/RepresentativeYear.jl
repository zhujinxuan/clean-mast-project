module RepresentativeYear

using ..Types.MastTimeSeries: TimeSeriesData
using ..Types.ReconstructMeso: TrainingTimeRange
using ..Types.RepresentativeYear: CalibrationResults
using Dates

include("./RepresentativeYear/Analysis.jl")
using .Analysis

"""
Main function to perform representative year calibration
"""
function calibrate_to_representative_year(
    mast_ts::TimeSeriesData,
    meso_ts::TimeSeriesData,
    mast_time_range::TrainingTimeRange;
    target_height::Float64=120.0  # Default to 120m
)::TimeSeriesData
    # Find target sensor
    target_sensor = find_target_sensor(mast_ts, target_height)
    if isnothing(target_sensor)
        error("No suitable wind speed sensor found near height $(target_height)m")
    end
    
    # Calculate mean speeds for target sensor
    meso_full_mean = calculate_mean_speed(meso_ts, target_sensor)
    meso_range_mean = calculate_mean_speed(
        filter(row -> mast_time_range.min <= row.timestamp <= mast_time_range.max, meso_ts),
        target_sensor
    )
    
    # Check if calibration is needed
    needs_calibration = is_calibration_needed(meso_full_mean, meso_range_mean)
    
    if !needs_calibration
        return mast_ts
    end
    
    # Find representative year start DateTime
    ref_year_start = find_representative_year(meso_ts, meso_full_mean)
    
    # Calculate directional calibrations
    directional_cals = calculate_directional_calibrations(
        mast_ts,
        meso_ts,
        mast_time_range,
        ref_year_start,
        target_sensor
    )
    
    # Create calibration results
    calibration = CalibrationResults(
        ref_year_start,
        target_sensor,
        meso_range_mean / meso_full_mean,
        directional_cals,
        true
    )
    
    # Apply calibration
    apply_calibration(mast_ts, calibration)
end

export calibrate_to_representative_year

end 