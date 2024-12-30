module Reconstruction

using DataFrames
using ...Types.MastTimeSeries: TimeSeriesData
using ...Types.CleanMastConfig: TimeRange
using ...Types.ReconstructMeso: WindSpeedTrainResults, WindDirectionTrainResults, TrainingTimeRange
using ..DataProcessing: prepare_timeseries
using Dates

"""
Calculate interpolated value between two points, handling both linear and circular interpolation
"""
function calculate_interpolated_value(
    before_val::Float64,
    after_val::Float64,
    t_frac::Float64,
    is_circular::Bool=false
)::Float64
    if is_circular
        angle_diff = mod(after_val - before_val + 180, 360) - 180
        return mod(before_val + t_frac * angle_diff, 360)
    else
        return before_val + t_frac * (after_val - before_val)
    end
end

"""
Interpolate meso values for given hours, handling both linear and circular interpolation
"""
function interpolate_meso_values(
    meso_ts::TimeSeriesData,
    unique_hours::Vector{DateTime},
    meso_col::Symbol;
    is_circular::Bool=false
)::Dict{DateTime, Float64}
    # Find all indices for the hours
    hour_indices = map(hour -> (
        hour=hour, 
        idx=findfirst(==(hour), meso_ts.df.timestamp)
    ), unique_hours)
    
    # Separate into direct values and those needing interpolation
    direct_values = filter(hi -> !isnothing(hi.idx) && !ismissing(meso_ts.df[hi.idx, meso_col]), hour_indices)
    need_interpolation = filter(hi -> isnothing(hi.idx) || ismissing(meso_ts.df[hi.idx, meso_col]), hour_indices)
    
    # Create dictionary with direct values
    meso_values = Dict(
        hi.hour => meso_ts.df[hi.idx, meso_col] for hi in direct_values
    )
    
    # Handle interpolation cases
    interpolated_values = map(need_interpolation) do hi
        hour = hi.hour
        before_idx = findlast(t -> !ismissing(meso_ts.df[t, meso_col]) && 
                                meso_ts.df.timestamp[t] < hour, 1:nrow(meso_ts.df))
        after_idx = findfirst(t -> !ismissing(meso_ts.df[t, meso_col]) && 
                                meso_ts.df.timestamp[t] > hour, 1:nrow(meso_ts.df))
        
        if !isnothing(before_idx) && !isnothing(after_idx)
            before_val = meso_ts.df[before_idx, meso_col]
            after_val = meso_ts.df[after_idx, meso_col]
            before_time = meso_ts.df.timestamp[before_idx]
            after_time = meso_ts.df.timestamp[after_idx]
            
            t_frac = (hour - before_time) / (after_time - before_time)
            value = calculate_interpolated_value(before_val, after_val, t_frac, is_circular)
            
            return (hour=hour, value=value)
        end
        return nothing
    end
    
    # Merge interpolated values into the result
    merge!(meso_values, Dict(
        iv.hour => iv.value for iv in filter(!isnothing, interpolated_values)
    ))
    
    return meso_values
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
        meso_col = train_result.mesoSensor.columnName
        
        # Find missing values in mast data
        missing_mask = ismissing.(result_df[!, col_name])
        
        if any(missing_mask)
            # Get timestamps for missing data
            missing_times = result_df[missing_mask, :timestamp]
            
            # Round to nearest hour for meso data lookup
            meso_hours = floor.(missing_times, Hour(1))
            unique_hours = unique(meso_hours)
            
            # Create interpolated meso values for each hour
            meso_values = interpolate_meso_values(meso_ts, unique_hours, meso_col, is_circular=false)
            
            # Fill missing values using interpolated meso data
            for (i, missing_time) in enumerate(missing_times)
                hour = meso_hours[i]
                if haskey(meso_values, hour)
                    result_df[findall(missing_mask)[i], col_name] = 
                        train_result.slope * meso_values[hour] + train_result.intercept
                end
            end
        end
    end
    
    # Fill wind direction gaps (similar approach but with directional interpolation)
    for (col_name, train_result) in wd_results
        meso_col = train_result.mesoSensor.columnName
        
        missing_mask = ismissing.(result_df[!, col_name])
        
        if any(missing_mask)
            missing_times = result_df[missing_mask, :timestamp]
            meso_hours = floor.(missing_times, Hour(1))
            unique_hours = unique(meso_hours)
            
            meso_values = interpolate_meso_values(meso_ts, unique_hours, meso_col, is_circular=true)
            
            # Fill missing values using interpolated meso data
            for (i, missing_time) in enumerate(missing_times)
                hour = meso_hours[i]
                if haskey(meso_values, hour)
                    result_df[findall(missing_mask)[i], col_name] = 
                        mod(meso_values[hour] + train_result.diff, 360)
                end
            end
        end
    end
    
    TimeSeriesData(result_df, mast_ts.sensors)
end

export fill_missing_data

end 