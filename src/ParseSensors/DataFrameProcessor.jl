# src/ParseSensors/DataFrameProcessor.jl
"""
Functions for processing a DataFrame after data has been loaded.
This includes timestamp normalization and column transformations.
"""
module DataFrameProcessor

using DataFrames, Dates
using ...Types.SensorColumns: ParsedSensor

export normalize_timestamp!, transform_columns!

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

    missing_timestamps = count(ismissing, df[!, timestamp_column])
    if missing_timestamps > 0
        @warn "Found $missing_timestamps missing timestamps."
    end

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
    group_sensors_by_column_name(sensors::Vector{ParsedSensor})::Dict{Symbol, Vector{ParsedSensor}}

Group sensors by their target columnName.
This identifies which sensors will be renamed to the same column.
"""
function group_sensors_by_column_name(sensors::Vector{ParsedSensor})::Dict{Symbol, Vector{ParsedSensor}}
    grouped = Dict{Symbol, Vector{ParsedSensor}}()
    for sensor in sensors
        if !haskey(grouped, sensor.columnName)
            grouped[sensor.columnName] = ParsedSensor[]
        end
        push!(grouped[sensor.columnName], sensor)
    end
    return grouped
end

"""
    calculate_overlap_percentage(df::DataFrame, col1::Symbol, col2::Symbol)::Float64

Calculate the percentage of rows where both columns have non-missing data.
Returns percentage from 0.0 to 100.0.
"""
function calculate_overlap_percentage(df::DataFrame, col1::Symbol, col2::Symbol)::Float64
    if !(String(col1) in names(df) && String(col2) in names(df))
        return 0.0
    end

    both_valid = count(.!ismissing.(df[!, col1]) .& .!ismissing.(df[!, col2]))
    total = nrow(df)

    return total > 0 ? (both_valid / total) * 100.0 : 0.0
end

"""
    merge_sensor_group(sensor_group::Vector{ParsedSensor}, df::DataFrame)::ParsedSensor

Merge a group of ParsedSensors that target the same columnName.
- Combines originalColumnNames from all sensors
- Calculates overlap and warns if > 10%
- Returns a single merged ParsedSensor
"""
function merge_sensor_group(sensor_group::Vector{ParsedSensor}, df::DataFrame)::ParsedSensor
    if length(sensor_group) == 1
        return sensor_group[1]
    end

    first_sensor = sensor_group[1]
    all_original_names = Symbol[]

    for sensor in sensor_group
        append!(all_original_names, sensor.originalColumnNames)
    end

    if length(all_original_names) > 1
        for i in 1:(length(all_original_names)-1)
            for j in (i+1):length(all_original_names)
                overlap_pct = calculate_overlap_percentage(df, all_original_names[i], all_original_names[j])
                if overlap_pct > 10.0
                    @warn "Significant overlap detected when merging columns" target=first_sensor.columnName sources=all_original_names overlap_percentage=round(overlap_pct, digits=2)
                end
            end
        end
    end

    return ParsedSensor(
        first_sensor.columnName,
        first_sensor.columnFormat,
        first_sensor.sensorType,
        first_sensor.sensorDirection,
        first_sensor.height,
        first_sensor.statType,
        first_sensor.unit,
        originalColumnNames=all_original_names,
        multiplier=first_sensor.multiplier
    )
end

"""
    merge_duplicate_sensors(sensors::Vector{ParsedSensor}, df::DataFrame)::Vector{ParsedSensor}

Merge sensors that have duplicate target columnNames.
Returns a vector where duplicates are merged into single ParsedSensor objects.
"""
function merge_duplicate_sensors(sensors::Vector{ParsedSensor}, df::DataFrame)::Vector{ParsedSensor}
    grouped = group_sensors_by_column_name(sensors)
    merged_sensors = ParsedSensor[]

    for (col_name, group) in grouped
        merged = merge_sensor_group(group, df)
        push!(merged_sensors, merged)
    end

    return merged_sensors
end

"""
    merge_columns!(df::DataFrame, target_name::Symbol, source_names::Vector{Symbol})

Merge multiple source columns into a single target column.
Strategy: Use the latter column's data when both have values (latter wins).
"""
function merge_columns!(df::DataFrame, target_name::Symbol, source_names::Vector{Symbol})
    available_sources = filter(name -> String(name) in names(df), source_names)

    if isempty(available_sources)
        @warn "No source columns found for merging" target=target_name sources=source_names
        return
    end

    merged_data = missings(eltype(df[!, available_sources[1]]), nrow(df))

    for source_name in available_sources
        source_col = df[!, source_name]
        for i in 1:nrow(df)
            if !ismissing(source_col[i])
                merged_data[i] = source_col[i]
            end
        end
    end

    df[!, target_name] = merged_data

    for source_name in available_sources
        if source_name != target_name
            select!(df, Not(source_name))
        end
    end
end

"""
    apply_column_transformations!(df::DataFrame, sensors::Vector{ParsedSensor})

Rename or merge columns in the DataFrame based on ParsedSensor metadata.
- Single originalColumnName: simple rename
- Multiple originalColumnNames: merge columns (latter wins)
"""
function apply_column_transformations!(df::DataFrame, sensors::Vector{ParsedSensor})
    for sensor in sensors
        if length(sensor.originalColumnNames) == 1
            original_name = sensor.originalColumnNames[1]
            if original_name != sensor.columnName && String(original_name) in names(df)
                rename!(df, original_name => sensor.columnName)
            end
        else
            merge_columns!(df, sensor.columnName, sensor.originalColumnNames)
        end
    end
end

"""
    apply_multipliers!(df::DataFrame, sensors::Vector{ParsedSensor})

Apply multiplier transformations to columns based on ParsedSensor metadata.
"""
function apply_multipliers!(df::DataFrame, sensors::Vector{ParsedSensor})
    for sensor in sensors
        if !isnothing(sensor.multiplier) && sensor.multiplier != 1.0
            if String(sensor.columnName) in names(df)
                df[!, sensor.columnName] .*= sensor.multiplier
            else
                @warn "Column not found for applying multiplier" column=sensor.columnName
            end
        end
    end
end

"""
    transform_columns!(df::DataFrame, sensors::Vector{ParsedSensor})::Tuple{DataFrame, Vector{ParsedSensor}}

Main function: Transform DataFrame columns (rename, merge, apply multipliers).
This function:
1. Merges duplicate sensors (same target columnName)
2. Renames or merges columns in the DataFrame
3. Applies multipliers to transformed columns

Returns a tuple of (transformed DataFrame, merged sensors).
"""
function transform_columns!(df::DataFrame, sensors::Vector{ParsedSensor})::Tuple{DataFrame, Vector{ParsedSensor}}
    df_transformed = copy(df)

    merged_sensors = merge_duplicate_sensors(sensors, df_transformed)

    apply_column_transformations!(df_transformed, merged_sensors)

    apply_multipliers!(df_transformed, merged_sensors)

    return (df_transformed, merged_sensors)
end

end
