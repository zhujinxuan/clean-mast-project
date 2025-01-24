module Reconstruction

using DataFrames
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.CleanMastConfig: TimeRange
using ...Types.ReconstructMeso: WindSpeedTrainResults, WindDirectionTrainResults, TrainingTimeRange,
                               WindSpeedTrainResult, WindDirectionTrainResult, WindSpeedSectorModel
using ..DataProcessing: prepare_training_data
using ...Types.Sector: degree_diff
using Dates

"""
Get the appropriate wind speed sector model based on meso direction
"""
function get_sector_model(direction::Float64, train_result::WindSpeedTrainResult)
    # Find the sector that contains this direction
    sector_model = findfirst(model -> 
        model.sector_start <= direction < model.sector_end, 
        train_result.sector_models)
    
    # If no sector found (shouldn't happen with proper setup), use first sector
    isnothing(sector_model) && return train_result.sector_models[1]
    
    train_result.sector_models[sector_model]
end

"""
Ensure DataFrame has all timestamps in the training range
"""
function ensure_training_range(df::DataFrame, time_range::TrainingTimeRange)::DataFrame
    # Create complete timestamp sequence
    complete_df = DataFrame(timestamp = collect(time_range.min:Minute(10):time_range.max))
    
    # Join with existing data, filling missing values
    result_df = leftjoin(complete_df, df, on = :timestamp)
    
    sort!(result_df, :timestamp)
    result_df
end

"""
Fill missing wind speed data using trained correlations (in-place)
"""
function fill_missing_data_ws!(df::DataFrame, interpolated_meso_ts::TimeSeriesData, ws_results::WindSpeedTrainResults)
    for (col_name, train_result) in ws_results
        meso_speed_col = train_result.mesoSpeedSensor.columnName
        meso_dir_col = train_result.mesoDirectionSensor.columnName
        
        # Get all timestamps where we have mast data (missing or not)
        mast_times = df.timestamp
        
        # Create a DataFrame with mast timestamps and select matching meso data
        mast_df = DataFrame(timestamp = mast_times)
        meso_data = select(
            interpolated_meso_ts.df[in.(interpolated_meso_ts.df.timestamp, Ref(Set(mast_times))), :],
            :timestamp,
            meso_speed_col => :meso_ws,
            meso_dir_col => :meso_wd
        )

        sector_models = map(meso_data.meso_wd) do wd
            if ismissing(wd)
                return nothing
            end
            return get_sector_model(wd, train_result)
        end

        meso_data.slope = map(sector_models) do model
            if isnothing(model)
                return missing
            end
            return model.slope
        end

        meso_data.intercept = map(sector_models) do model
            if isnothing(model)
                return missing
            end
            return model.intercept
        end

        meso_data.mast_ws = map(meso_data.meso_ws, meso_data.slope, meso_data.intercept) do ws, slope, intercept
            if ismissing(ws) || ismissing(slope) || ismissing(intercept)
                return missing
            end
            minimum([maximum([ws * slope + intercept,0.5]), 25])
        end

        # Only fill in missing values in the df
        missing_mask = ismissing.(df[!, col_name])
        df[missing_mask, col_name] = meso_data.mast_ws[missing_mask]
    end
end

"""
Fill missing wind direction data using trained correlations (in-place)
"""
function fill_missing_data_wd!(df::DataFrame, interpolated_meso_ts::TimeSeriesData, wd_results::WindDirectionTrainResults)
    for (col_name, train_result) in wd_results
        meso_col = train_result.mesoSensor.columnName
        
        # Get all timestamps where we have mast data (missing or not)
        mast_times = df.timestamp
        missing_mask = ismissing.(df[!, col_name])
        
        # Process each timestamp where we need to fill data
        if any(missing_mask)
            missing_times = mast_times[missing_mask]
            missing_indices = findall(missing_mask)
            
            for (idx, missing_time) in zip(missing_indices, missing_times)
                meso_idx = findfirst(==(missing_time), interpolated_meso_ts.df.timestamp)
                
                if !isnothing(meso_idx)
                    meso_val = interpolated_meso_ts.df[meso_idx, meso_col]
                    if !ismissing(meso_val)
                        df[idx, col_name] = mod(meso_val + train_result.diff, 360)
                    end
                end
            end
        end
    end
end

"""
Fill missing data using trained correlations, handling different time resolutions
and interpolating missing meso data. Note that interpolated_meso_ts is already interpolated to 10-minute intervals.

Parameters
----------
mast_ts : TimeSeriesData
    The mast time series data with missing values to fill
interpolated_meso_ts : TimeSeriesData 
    The meso time series data, already interpolated to 10-minute intervals
training_time_range : TrainingTimeRange
    The time range to fill data for
ws_results : WindSpeedTrainResults
    The trained wind speed correlations
wd_results : WindDirectionTrainResults
    The trained wind direction correlations

Returns
-------
TimeSeriesData
    The mast time series with missing values filled where possible

"""
function fill_missing_data(mast_ts::TimeSeriesData, interpolated_meso_ts::TimeSeriesData,
                         training_time_range::TrainingTimeRange, 
                         ws_results::WindSpeedTrainResults,
                         wd_results::WindDirectionTrainResults)::TimeSeriesData
    
    # Create a copy of the DataFrame and ensure all timestamps exist
    result_df = ensure_training_range(copy(mast_ts.df), training_time_range)
    
    # Fill wind speed and direction sequentially
    fill_missing_data_ws!(result_df, interpolated_meso_ts, ws_results)
    fill_missing_data_wd!(result_df, interpolated_meso_ts, wd_results)
    
    TimeSeriesData(result_df, mast_ts.sensors)
end

export fill_missing_data, fill_missing_data_ws!, fill_missing_data_wd!, ensure_training_range

end 