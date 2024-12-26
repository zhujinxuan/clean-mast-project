module Reconstruction

using DataFrames
using ...Types.MastTimeSeries: TimeSeriesData
using ...Types.CleanMastConfig: TimeRange
using ...Types.ReconstructMeso: WindSpeedTrainResults, WindDirectionTrainResults
using ..DataProcessing: prepare_timeseries
using Dates

"""
Fill missing data using trained correlations
"""
function fill_missing_data(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData,
                         time_range::TimeRange, 
                         ws_results::WindSpeedTrainResults,
                         wd_results::WindDirectionTrainResults)::TimeSeriesData
    # Ensure complete timeseries for mast data
    complete_mast = prepare_timeseries(mast_ts, time_range, Minute(10))
    
    # Prepare meso data with hourly resolution
    complete_meso = prepare_timeseries(meso_ts, time_range, Minute(60))
    
    # Create result DataFrame
    result_df = copy(complete_mast.df)
    
    # Fill wind speed gaps
    for (col_name, train_result) in ws_results
        meso_col = train_result.mesoSensor.columnName
        
        # Find missing values in mast data
        missing_mask = ismissing.(result_df[!, col_name])
        
        # Fill where we have meso data
        result_df[missing_mask, col_name] = @. train_result.slope * 
            complete_meso.df[missing_mask, meso_col] + train_result.intercept
    end
    
    # Fill wind direction gaps
    for (col_name, train_result) in wd_results
        meso_col = train_result.mesoSensor.columnName
        
        # Find missing values in mast data
        missing_mask = ismissing.(result_df[!, col_name])
        
        # Fill where we have meso data
        result_df[missing_mask, col_name] = @. mod(
            complete_meso.df[missing_mask, meso_col] + train_result.diff, 360)
    end
    
    TimeSeriesData(result_df, complete_mast.sensors)
end

export fill_missing_data

end 