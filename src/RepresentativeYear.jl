module RepresentativeYear

using ..Types.MastTimeSeries: TimeSeriesData, TimeRange
using ..Types.RepresentativeYear: CalibrationResults
using ..Types.SpeedReferenceModel.SectorizedRegression: SectorizedRegressionModel
using Dates

include("./RepresentativeYear/Analysis.jl")
using ..Types.SpeedReferenceModel.SectorizedRegression: find_pair_from_mast_sensor
using .Analysis

"""
Main function to perform representative year calibration
"""
function calibrate_to_representative_year(
    mast_ts::TimeSeriesData,
    meso_ts::TimeSeriesData,
    mast_time_range::TimeRange,
    sectorized_regression_model::SectorizedRegressionModel;
    target_height::Float64=120.0  # Default to 120m
)::TimeSeriesData
    # Find target sensors in both mast and meso data
    mast_sensor = find_target_mast_sensor(mast_ts, target_height)
    if isnothing(mast_sensor)
        error("No suitable wind speed sensor found in mast data near height $(target_height)m")
    end

    pair = find_pair_from_mast_sensor(sectorized_regression_model, mast_sensor)
    if (isnothing(pair))
        error("No suitable meso wind speed sensor found from pre-trained model")
    end
    meso_sensor = pair.meso_speed_sensor

    # Calculate mean speeds for meso sensor
    meso_full_mean = calculate_mean_speed(meso_ts, meso_sensor)
    
    # Filter DataFrame and create new TimeSeriesData for training range
    training_df = filter(
        row -> mast_time_range.min <= row.timestamp <= mast_time_range.max, 
        meso_ts.df
    )
    training_ts = TimeSeriesData(training_df, meso_ts.sensors)
    meso_range_mean = calculate_mean_speed(training_ts, meso_sensor)
    
    # Check if calibration is needed
    needs_calibration = is_calibration_needed(meso_full_mean, meso_range_mean)
    
    if !needs_calibration
        return mast_ts
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
    directional_cals = map(pair.sectors) do sector
        # Extract slope directly from the sector
        slope = sector.slope
        # Calculate meso speed difference for this sector
        sector_meso_diff = sector_meso_diff_df[sector.name, :meso_speed_diff]
        
        DirectionalCalibration(sector.center, slope, sector_meso_diff)
    end
    
    # Create calibration results
    calibration = CalibrationResults(
        ref_year_start,
        mast_sensor,
        directional_cals,
        true
    )
    
    # Apply calibration
    apply_calibration(mast_ts, calibration)
end

export calibrate_to_representative_year

end 