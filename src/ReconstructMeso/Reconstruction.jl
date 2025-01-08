module Reconstruction

using DataFrames
using ...Types.MastTimeSeries: TimeSeriesData
using ...Types.CleanMastConfig: TimeRange
using ...Types.ReconstructMeso: WindSpeedTrainResults, WindDirectionTrainResults, TrainingTimeRange,
                               WindSpeedTrainResult, WindDirectionTrainResult, WindSpeedSectorModel
using ..DataProcessing: prepare_training_data
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
Fill missing wind speed data using trained correlations
"""
function fill_missing_data_ws(df::DataFrame, meso_ts::TimeSeriesData, ws_results::WindSpeedTrainResults)::DataFrame
    result_df = copy(df)
    
    for (col_name, train_result) in ws_results
        meso_speed_col = train_result.mesoSpeedSensor.columnName
        meso_dir_col = train_result.mesoDirectionSensor.columnName
        
        missing_mask = ismissing.(result_df[!, col_name])
        !any(missing_mask) && continue
        
        # Get all missing timestamps
        missing_times = result_df[missing_mask, :timestamp]
        
        # Create a DataFrame with missing timestamps and corresponding meso data
        meso_data = DataFrame(
            timestamp = missing_times,
            meso_ws = map(t -> get(meso_ts.df[findfirst(==(t), meso_ts.df.timestamp), :], meso_speed_col, missing), missing_times),
            meso_wd = map(t -> get(meso_ts.df[findfirst(==(t), meso_ts.df.timestamp), :], meso_dir_col, missing), missing_times)
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

        # refill result_df with meso_data.mast_ws
        for (i, t) in enumerate(meso_data.timestamp)
            result_df[findfirst(==(t), result_df.timestamp), col_name] = meso_data.mast_ws[i]
        end
    end
    
    result_df
end

"""
Fill missing wind direction data using trained correlations
"""
function fill_missing_data_wd(df::DataFrame, meso_ts::TimeSeriesData, wd_results::WindDirectionTrainResults)::DataFrame
    result_df = copy(df)
    
    for (col_name, train_result) in wd_results
        meso_col = train_result.mesoSensor.columnName
        missing_mask = ismissing.(result_df[!, col_name])
        
        if any(missing_mask)
            missing_times = result_df[missing_mask, :timestamp]
            missing_indices = findall(missing_mask)
            
            # Process each missing timestamp
            for (idx, missing_time) in zip(missing_indices, missing_times)
                meso_idx = findfirst(==(missing_time), meso_ts.df.timestamp)
                
                if !isnothing(meso_idx)
                    meso_val = meso_ts.df[meso_idx, meso_col]
                    if !ismissing(meso_val)
                        result_df[idx, col_name] = mod(meso_val + train_result.diff, 360)
                    end
                end
            end
        end
    end
    
    result_df
end

"""
Fill missing data using trained correlations, handling different time resolutions
and interpolating missing meso data
"""
function fill_missing_data(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData,
                         training_time_range::TrainingTimeRange, 
                         ws_results::WindSpeedTrainResults,
                         wd_results::WindDirectionTrainResults)::TimeSeriesData
    
    # Fill wind speed and direction sequentially
    result_df = fill_missing_data_ws(mast_ts.df, meso_ts, ws_results)
    result_df = fill_missing_data_wd(result_df, meso_ts, wd_results)
    
    TimeSeriesData(result_df, mast_ts.sensors)
end

export fill_missing_data, fill_missing_data_ws, fill_missing_data_wd

end 