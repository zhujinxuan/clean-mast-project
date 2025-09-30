"""
    TrainMeso.jl

Module for training mesoscale reference models for wind speed and direction.
"""
module Core

using DataFrames
using Dates
using ...Types.MastTimeSeries: TimeSeriesData, TimeRange
using ...Types.Sector: DirectionSector, DIRECTION_16_SECTORS
using ...Types.MastReferenceModel: train
using ...Types.SpeedReferenceModel.SectorizedRegression: SectorizedRegressionModel, SectorizedRegressionParams
using ...Types.DirectionReferenceModel.DirectionOffset: DirectionOffsetModel, DirectionOffsetParams
using ...TimeSeriesProcessing.Regularization: ensure_regular_intervals, validate_intervals
using ...TimeSeriesProcessing.Interpolation: interpolate_timeseries
using ...TimeSeriesProcessing.IntervalDetection: detect_representative_interval

export train_meso_windspeed_sectorized, train_meso_winddirection_directionoffset

"""
    prepare_training_data(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData)::Tuple{TimeSeriesData, TimeSeriesData}

Prepare mast and meso data for training by:
1. Detecting representative interval and ensuring mast data has regular intervals
2. Interpolating meso data to match mast timestamps
"""
function prepare_training_data(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData)::Tuple{TimeSeriesData, TimeSeriesData}
    # Calculate time range from mast data
    time_range = TimeRange(
        minimum(mast_ts.df.timestamp),
        maximum(mast_ts.df.timestamp)
    )
    
    # Detect representative interval and ensure mast data has regular intervals
    representative_interval = detect_representative_interval(mast_ts)
    if !validate_intervals(mast_ts, representative_interval)
        mast_ts = ensure_regular_intervals(mast_ts, time_range, representative_interval)
    end

    
    # Interpolate meso data to match mast timestamps
    meso_ts = interpolate_timeseries(meso_ts, mast_ts.df.timestamp)
    
    # Verify alignment
    mast_times = Set(mast_ts.df.timestamp)
    meso_times = Set(meso_ts.df.timestamp)
    println("  Timestamps match: $(mast_times == meso_times)")
    if mast_times != meso_times
        println("  Missing in meso: $(length(setdiff(mast_times, meso_times))) timestamps")
        println("  Extra in meso: $(length(setdiff(meso_times, mast_times))) timestamps")
    end
    
    return mast_ts, meso_ts
end

"""
    train_meso_windspeed_sectorized(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData, 
                                  sector_mode::String="16-sector")::SectorizedRegressionModel

Train a sectorized regression model for wind speed reconstruction.

# Arguments
- `mast_ts::TimeSeriesData`: Mast time series data
- `meso_ts::TimeSeriesData`: Mesoscale time series data
- `sector_mode::String`: Either "16-sector" or "1-sector"

# Returns
- `SectorizedRegressionModel`: Trained model for wind speed reconstruction

# Notes
- For "16-sector", uses standard 16 wind direction sectors
- For "1-sector", uses a single 360° sector
"""
function train_meso_windspeed_sectorized(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData, 
                                       sector_mode::String="16-sector")::SectorizedRegressionModel
    # Input validation
    if !(sector_mode in ["16-sector", "1-sector"])
        throw(ArgumentError("sector_mode must be either '16-sector' or '1-sector'"))
    end
    
    # Prepare data
    mast_ts, meso_ts = prepare_training_data(mast_ts, meso_ts)
    
    # Select sectors based on mode
    sectors = if sector_mode == "16-sector"
        DIRECTION_16_SECTORS
    else
        [DirectionSector("ALL", 0.0, 360.0)]
    end
    
    # Train model
    params = SectorizedRegressionParams(
        sectors
    )
    train(SectorizedRegressionModel, params, mast_ts, meso_ts)
end

"""
    train_meso_winddirection_directionoffset(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData)::DirectionOffsetModel

Train a direction offset model for wind direction reconstruction.

# Arguments
- `mast_ts::TimeSeriesData`: Mast time series data
- `meso_ts::TimeSeriesData`: Mesoscale time series data

# Returns
- `DirectionOffsetModel`: Trained model for wind direction reconstruction
"""
function train_meso_winddirection_directionoffset(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData)::DirectionOffsetModel
    # Prepare data
    mast_ts, meso_ts = prepare_training_data(mast_ts, meso_ts)
    
    # Train model
    train(DirectionOffsetModel, DirectionOffsetParams(), mast_ts, meso_ts)
end

end # module 