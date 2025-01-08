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
Fill missing data using trained correlations, handling different time resolutions
and interpolating missing meso data
"""
function fill_missing_data(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData,
                         training_time_range::TrainingTimeRange, 
                         ws_results::WindSpeedTrainResults,
                         wd_results::WindDirectionTrainResults)::TimeSeriesData
    
    result_df = copy(mast_ts.df)
    
    # Fill wind speed gaps
    for (col_name, train_result) in ws_results
        meso_speed_col = train_result.mesoSensor.columnName
        meso_dir_col = train_result.mesoSensor.columnName
        
        # Find missing values in mast data
        missing_mask = ismissing.(result_df[!, col_name])
        
        if any(missing_mask)
            # Get timestamps for missing data
            missing_times = result_df[missing_mask, :timestamp]
            
            # Get corresponding meso values
            for (i, missing_time) in enumerate(missing_times)
                # Find exact timestamp in meso data
                meso_idx = findfirst(==(missing_time), meso_ts.df.timestamp)
                isnothing(meso_idx) && continue
                
                meso_speed = meso_ts.df[meso_idx, meso_speed_col]
                meso_dir = meso_ts.df[meso_idx, meso_dir_col]
                
                if !ismissing(meso_speed) && !ismissing(meso_dir)
                    # Get appropriate sector model
                    sector_model = get_sector_model(meso_dir, train_result)
                    
                    # Apply model
                    result_df[findall(missing_mask)[i], col_name] = 
                        sector_model.slope * meso_speed + sector_model.intercept
                end
            end
        end
    end
    
    # Fill wind direction gaps
    for (col_name, train_result) in wd_results
        meso_col = train_result.mesoSensor.columnName
        
        missing_mask = ismissing.(result_df[!, col_name])
        
        if any(missing_mask)
            # Get timestamps for missing data
            missing_times = result_df[missing_mask, :timestamp]
            
            # Fill missing values using interpolated meso data
            for (i, missing_time) in enumerate(missing_times)
                meso_idx = findfirst(==(missing_time), meso_ts.df.timestamp)
                isnothing(meso_idx) && continue
                
                meso_val = meso_ts.df[meso_idx, meso_col]
                if !ismissing(meso_val)
                    result_df[findall(missing_mask)[i], col_name] = 
                        mod(meso_val + train_result.diff, 360)
                end
            end
        end
    end
    
    TimeSeriesData(result_df, mast_ts.sensors)
end

export fill_missing_data

end 