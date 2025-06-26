# src/ParseSensors/DataFrameProcessor.jl
"""
Functions for processing a DataFrame after data has been loaded.
This includes timestamp normalization and column transformations.
"""
module DataFrameProcessor

using DataFrames, Dates
using ...Types.SensorColumns: ParsedSensor

export normalize_timestamp!, rename_and_apply_multipliers!

"""
    normalize_timestamp!(df::DataFrame, timestamp_column::String)

Normalize the timestamp column to the required format.
- Converts the column to DateTime if it's not already.
- Renames the column to `:timestamp`.
"""
function normalize_timestamp!(df::DataFrame, timestamp_column::String)
    if !(timestamp_column in names(df))
        error("Timestamp column '$timestamp_column' not found in DataFrame.")
    end
    
    # Check for missing values in timestamp column
    missing_timestamps = count(ismissing, df[!, timestamp_column])
    if missing_timestamps > 0
        @warn "Found $missing_timestamps missing timestamps."
    end
    
    # Convert timestamp column to DateTime if it's not already
    if eltype(df[!, timestamp_column]) != DateTime
        try
            df[!, timestamp_column] = DateTime.(df[!, timestamp_column])
        catch e
            @error "Failed to convert timestamp column to DateTime" exception=e
            rethrow()
        end
    end
    
    rename!(df, timestamp_column => :timestamp)
end

"""
    rename_and_apply_multipliers!(df::DataFrame, sensors::Vector{ParsedSensor})

Apply sensor configurations to a DataFrame.
- Renames columns from their original names to the new parsed names.
- Applies any specified multipliers to the column data.
"""
function rename_and_apply_multipliers!(df::DataFrame, sensors::Vector{ParsedSensor})::DataFrame
    df_transformed = copy(df) # Avoid modifying the original DataFrame in place
    
    for sensor in sensors
        # Rename column if needed
        if sensor.originalColumnName != sensor.columnName
            if string(sensor.originalColumnName) in names(df_transformed)
                rename!(df_transformed, sensor.originalColumnName => sensor.columnName)
            else
                @warn "Original column $(sensor.originalColumnName) not found for renaming."
            end
        end
        
        # Apply multiplier if it exists
        if !isnothing(sensor.multiplier) && sensor.multiplier != 1.0
            if string(sensor.columnName) in names(df_transformed)
                df_transformed[!, sensor.columnName] .*= sensor.multiplier
            else
                @warn "Column $(sensor.columnName) not found for applying multiplier."
            end
        end
    end
    
    return df_transformed
end

end 