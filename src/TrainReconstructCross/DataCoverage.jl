"""
    DataCoverage.jl

Time series coverage analysis for cross-mast reconstruction.
Analyzes overlap periods and concurrent data availability between different masts.
"""
module DataCoverage

using DataFrames
using Dates
using Statistics
using DataFramesMeta

import ...Types.MastTimeSeries: TimeSeriesData
import ...Types.SensorColumns: SensorColumn
import ...Types.CrossMastAnalysisResults: MastPairCoverage

export analyze_mast_pair_coverage, find_highest_wind_speed_sensor, get_valid_timestamps, calculate_potential_timestamps

"""
    analyze_mast_pair_coverage(target_ts::TimeSeriesData, source_ts::TimeSeriesData)::MastPairCoverage

Analyze time series overlap and data coverage between two masts using highest wind speed sensors.

# Arguments
- `target_ts::TimeSeriesData`: Target mast time series data
- `source_ts::TimeSeriesData`: Source mast time series data

# Returns
- `MastPairCoverage`: Coverage analysis results including overlap period and concurrent data statistics

# Description
This function performs precise coverage analysis between two mast time series:
1. Finds the highest wind speed sensor (avg) for each mast
2. Uses dropmissing to get valid timestamps for each sensor
3. Finds overlapped timestamps between the two masts
4. Calculates days based on 10-minute intervals * timestamp count
5. Calculates coverage statistics based on actual valid data

# Example
```julia
coverage = analyze_mast_pair_coverage(target_mast_data, source_mast_data)
```
"""
function analyze_mast_pair_coverage(target_ts::TimeSeriesData, source_ts::TimeSeriesData)::Union{MastPairCoverage, Nothing}
    # Find highest wind speed sensors for each mast
    target_highest_sensor = find_highest_wind_speed_sensor(target_ts.sensors)
    source_highest_sensor = find_highest_wind_speed_sensor(source_ts.sensors)
    
    if isnothing(target_highest_sensor) || isnothing(source_highest_sensor)
        @warn "No wind speed sensors found in one or both masts"
        return nothing
    end
    
    # Get valid timestamps for each mast using highest wind speed sensor
    target_valid_timestamps = get_valid_timestamps(target_ts.df, target_highest_sensor.columnName)
    source_valid_timestamps = get_valid_timestamps(source_ts.df, source_highest_sensor.columnName)
    
    if isempty(target_valid_timestamps) || isempty(source_valid_timestamps)
        @warn "No valid timestamps found for highest wind speed sensors"
        return nothing
    end
    
    # Find overlapped timestamps (intersection)
    overlapped_timestamps = intersect(Set(target_valid_timestamps), Set(source_valid_timestamps))
    overlapped_timestamps_sorted = sort(collect(overlapped_timestamps))
    
    if isempty(overlapped_timestamps_sorted)
        return nothing
    end
    
    # Calculate overlap period from actual overlapped timestamps
    overlap_start = minimum(overlapped_timestamps_sorted)
    overlap_end = maximum(overlapped_timestamps_sorted)
    concurrent_records = length(overlapped_timestamps_sorted)
    
    # Calculate days based on 10-minute intervals
    # 10 minutes * concurrent_records = total minutes of valid data
    # Convert to days: minutes / (60 * 24) where 60*24 is minutes per day
    overlap_days = (concurrent_records * 10.0) / (60.0 * 24.0)
    
    # Calculate coverage percentage based on potential overlap period
    potential_timestamps = calculate_potential_timestamps(overlap_start, overlap_end)
    coverage_percentage = if potential_timestamps > 0
        (concurrent_records / potential_timestamps) * 100.0
    else
        0.0
    end
    
    return MastPairCoverage(
        overlap_start = overlap_start,
        overlap_end = overlap_end,
        overlap_days = overlap_days,
        concurrent_records = concurrent_records,
        coverage_percentage = coverage_percentage
    )
end

"""
    find_highest_wind_speed_sensor(sensors::Vector{SensorColumn})::Union{SensorColumn, Nothing}

Find the highest wind speed sensor (avg statType) in a list of sensors.
"""
function find_highest_wind_speed_sensor(sensors :: Vector{SensorColumn})::Union{SensorColumn, Nothing}
    # Filter for wind speed sensors with avg statType
    wind_speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", sensors)
    
    if isempty(wind_speed_sensors)
        return nothing
    end
    
    # Return the sensor with the highest height
    maxH = maximum(s -> s.height, wind_speed_sensors)
    return first(filter(s -> s.height == maxH, wind_speed_sensors))
end

"""
    get_valid_timestamps(df::DataFrame, column_name::String)::Vector{DateTime}

Get all timestamps where the specified column has valid (non-missing) data.
"""
function get_valid_timestamps(df::DataFrame, column_name::Symbol)::Vector{DateTime}
    if !(column_name in propertynames(df))
        @debug "Column $column_name not found in dataframe"
        return DateTime[]
    end
    
    # Use dropmissing to get rows with valid data for the specified column
    valid_df = dropmissing(df, [(column_name)])
    
    if nrow(valid_df) == 0
        return DateTime[]
    end
    
    return valid_df.timestamp
end

"""
    calculate_potential_timestamps(start_time::DateTime, end_time::DateTime)::Int

Calculate the potential number of 10-minute intervals between two timestamps.
"""
function calculate_potential_timestamps(start_time::DateTime, end_time::DateTime)::Int
    if end_time <= start_time
        return 0
    end
    
    # Calculate total minutes between timestamps
    total_minutes = Dates.value(end_time - start_time) / (1000 * 60)  # Convert milliseconds to minutes
    
    # Calculate number of 10-minute intervals
    intervals = floor(Int, total_minutes / 10.0)
    
    return max(0, intervals)
end



end # module 