module WindSpeedTraining

using DataFrames
using Statistics
using Dates
using ...Types.ReconstructSingleMast
using ...Types.SensorColumns: SensorColumn
using ...Types.MastTimeSeries: TimeSeriesData

const DEFAULT_REFERENCE_HEIGHT = 50.0
export DEFAULT_REFERENCE_HEIGHT
const MIN_SHEAR_EXPONENT = -0.25
const MAX_SHEAR_EXPONENT = 1.25

"""
Calculate wind shear profile from valid measurements above reference height
"""
function calculate_wind_shear_profile(
    heights_speeds::Vector{Tuple{Float64, Float64}},
    reference_height::Float64=DEFAULT_REFERENCE_HEIGHT
)::Union{WindSpeedProfile, Nothing}
    length(heights_speeds) < 2 && return nothing
    
    # Unzip the tuples for calculations
    heights = first.(heights_speeds)
    speeds = last.(heights_speeds)
    
    # Calculate shear exponent using log-linear regression
    x = log.(heights ./ reference_height)
    y = log.(speeds ./ speeds[1])  # Use first speed as reference
    
    # Early exit: check for invalid logarithms or extreme ratios
    if any(isnan, x) || any(isnan, y) || any(isinf, x) || any(isinf, y)
        return nothing
    end
    
    # Simple linear regression to find shear exponent
    x_centered = x .- mean(x)
    y_centered = y .- mean(y)
    
    denominator = sum(x_centered.^2)
    shear_exponent = sum(x_centered .* y_centered) / denominator
    
    # Clamp shear exponent to valid range
    shear_exponent = clamp(shear_exponent, MIN_SHEAR_EXPONENT, MAX_SHEAR_EXPONENT)
    
    return WindSpeedProfile(reference_height, shear_exponent)
end
export calculate_wind_shear_profile

"""
Apply wind shear profile to estimate speed at target height
"""
function apply_wind_shear_profile(
    profile::WindSpeedProfile,
    reference_speed::Float64,
    target_height::Float64
)::Float64
    (target_height / profile.reference_height)^profile.shear_exponent * reference_speed
end
export apply_wind_shear_profile

"""
Calculate hourly average for wind speeds, handling missing values - OPTIMIZED VERSION
"""
function calculate_hourly_averages_optimized(
    hour_data::DataFrame,
    valid_sensors::Vector{SensorColumn}
)::Vector{Tuple{Float64, Float64}}
    # Early exit: check if hour_data is empty
    if isempty(hour_data)
        return Tuple{Float64, Float64}[]
    end
    
    # Extract heights and speeds using functional approach with early filtering
    heights_speeds = Tuple{Float64, Float64}[]
    
    for sensor in valid_sensors
        col_data = hour_data[!, sensor.columnName]
        # Early exit: skip sensors with no valid data
        valid_data = filter(!ismissing, col_data)
        if isempty(valid_data)
            continue
        end
        
        # Calculate mean, but check for reasonable values
        mean_speed = mean(valid_data)
        if mean_speed > 0 && mean_speed <= 50  # Reasonable wind speed range
            push!(heights_speeds, (sensor.height, mean_speed))
        end
    end
    
    return heights_speeds
end

"""
Create wind shear profile for a specific timestamp - OPTIMIZED VERSION
"""
function create_profile_for_target_optimized(
    hour_data::DataFrame,
    valid_sensors::Vector{SensorColumn}
)::Union{WindSpeedProfile, Nothing}
    # Early exit: insufficient sensors
    if length(valid_sensors) < 2
        return nothing
    end
    
    heights_speeds = calculate_hourly_averages_optimized(hour_data, valid_sensors)
    
    # Early exit: insufficient valid data
    if length(heights_speeds) < 2
        return nothing
    end
    
    return calculate_wind_shear_profile(heights_speeds)
end

"""
Pre-compute hourly data windows to avoid repeated DataFrame filtering
"""
function get_hourly_data_cached(
    df::DataFrame,
    timestamp::DateTime,
    hour_cache::Dict{DateTime, DataFrame}
)::DataFrame
    hour_start = floor(timestamp, Hour)
    
    # Return cached result if available
    if haskey(hour_cache, hour_start)
        return hour_cache[hour_start]
    end
    
    # Compute and cache the hourly data
    hour_data = df[hour_start .<= df.timestamp .< hour_start + Hour(1), :]
    hour_cache[hour_start] = hour_data
    
    return hour_data
end

"""
Reconstruct value for a single target using a profile - OPTIMIZED VERSION
"""
function reconstruct_target_optimized(
    target_row::DataFrameRow,
    valid_sensors::Vector{SensorColumn},
    target_col::Symbol,
    timestamp::DateTime,
    profile::WindSpeedProfile
)::Union{ReconstructedSuccess, ReconstructedFailure}
    # Find target sensor
    target_sensor_idx = findfirst(s -> s.columnName == target_col, valid_sensors)
    if isnothing(target_sensor_idx)
        return ReconstructedFailure(
            timestamp,
            target_col,
            "Target sensor not found in valid sensors"
        )
    end
    
    target_sensor = valid_sensors[target_sensor_idx]

    # Find valid speed measurements at this exact timestamp
    valid_speeds = Tuple{Float64, Float64}[]
    for sensor in valid_sensors
        speed_val = target_row[sensor.columnName]
        if !ismissing(speed_val) && speed_val > 0 && speed_val <= 100
            push!(valid_speeds, (sensor.height, speed_val))
        end
    end
    
    # Early exit: no valid reference measurements
    if isempty(valid_speeds)
        return ReconstructedFailure(
            timestamp,
            target_col,
            "No valid reference measurements found"
        )
    end
    
    # Find nearest height with valid measurement
    reference_height, reference_speed = reduce(valid_speeds; init=first(valid_speeds)) do closest, current
        abs(closest[1] - target_sensor.height) < abs(current[1] - target_sensor.height) ? closest : current
    end
    
    # Early exit: reference and target are the same sensor
    if reference_height ≈ target_sensor.height
        return ReconstructedFailure(
            timestamp,
            target_col,
            "Cannot reconstruct using same height sensor"
        )
    end
    
    reconstructed_speed = apply_wind_shear_profile(
        WindSpeedProfile(reference_height, profile.shear_exponent),
        reference_speed,
        target_sensor.height
    )
    
    # Validate reconstructed result
    if isnan(reconstructed_speed) || isinf(reconstructed_speed) || reconstructed_speed <= 0 || reconstructed_speed > 100
        return ReconstructedFailure(
            timestamp,
            target_col,
            "Reconstructed speed is invalid: $reconstructed_speed"
        )
    end
    
    return ReconstructedSuccess(
        timestamp,
        target_col,
        reconstructed_speed
    )
end

"""
Reconstruct missing wind speeds using shear profile
"""
function reconstruct_wind_speeds(
    data::TimeSeriesData,
    min_height::Float64=DEFAULT_REFERENCE_HEIGHT
)::Tuple{Vector{ReconstructedSuccess}, Vector{ReconstructedFailure}}
    # Filter valid wind speed sensors once
    valid_sensors = filter(data.sensors) do sensor
        sensor.sensorType == "WindSpeed" &&
        sensor.statType == "avg" &&
        sensor.height >= min_height
    end
    
    isempty(valid_sensors) && return ReconstructedSuccess[], ReconstructedFailure[]
    
    # Get reconstruction targets with filtered sensors
    targets = find_reconstruction_targets(data, "WindSpeed", "avg", min_height)
    
    # Process each target and its columns
    results = map(targets) do target
        profile = create_profile_for_target(data.df, target.timestamp, valid_sensors)
        
        if isnothing(profile)
            map(target.columns) do col 
                ReconstructedFailure(
                    target.timestamp,
                    col,
                    "Failed to calculate valid wind shear profile"
                )
            end
        else
            map(target.columns) do col
                reconstruct_target(
                    data.df,
                    valid_sensors,
                    col,
                    target.timestamp,
                    profile
                )
            end
        end
    end |> Iterators.flatten |> collect
    
    # Partition results into successes and failures
    successes = filter(r -> r isa ReconstructedSuccess, results)
    failures = filter(r -> r isa ReconstructedFailure, results)
    
    return successes, failures
end

export reconstruct_wind_speeds

"""
Reconstruct a single target column at a specific timestamp - REQUIRES 10-MINUTE INTERVALS
"""
function reconstruct_single_target(
    data::TimeSeriesData,
    target_col::Symbol,
    timestamp::DateTime,
    min_height::Float64=DEFAULT_REFERENCE_HEIGHT
)::Union{ReconstructedSuccess, ReconstructedFailure}
    # Filter valid wind speed sensors
    valid_sensors = filter(data.sensors) do sensor
        sensor.sensorType == "WindSpeed" &&
        sensor.statType == "avg" &&
        sensor.height >= min_height
    end
    
    # Early exit: insufficient sensors
    if length(valid_sensors) < 2
        return ReconstructedFailure(
            timestamp,
            target_col,
            "Insufficient wind speed sensors (need at least 2, found $(length(valid_sensors)))"
        )
    end
    
    # Validate time series format
    timestamps = data.df.timestamp
    if isempty(timestamps)
        return ReconstructedFailure(
            timestamp,
            target_col,
            "No timestamp data available"
        )
    end
    
    # Require 10-minute intervals
    if length(timestamps) > 1
        interval = timestamps[2] - timestamps[1]
        if interval != Minute(10)
            error("Time series must have 10-minute intervals. Found interval: $interval. Use regularization first.")
        end
    end
    
    # Fast arithmetic-based timestamp lookup for 10-minute intervals
    start_time = timestamps[1]
    minutes_elapsed = Dates.value(timestamp - start_time) ÷ (1000 * 60)  # Convert to minutes
    target_row_idx = (minutes_elapsed ÷ 10) + 1
    
    if target_row_idx < 1 || target_row_idx > length(timestamps) || timestamps[target_row_idx] != timestamp
        return ReconstructedFailure(
            timestamp,
            target_col,
            "Timestamp not found in regular 10-minute time series"
        )
    end
    
    target_row = data.df[target_row_idx, :]
    
    # Fast hourly data extraction using array arithmetic
    hour_start = floor(timestamp, Hour)
    hour_start_minutes = Dates.value(hour_start - start_time) ÷ (1000 * 60)
    hour_end_minutes = hour_start_minutes + 60
    
    hour_start_idx = max(1, (hour_start_minutes ÷ 10) + 1)
    hour_end_idx = min(length(timestamps), (hour_end_minutes ÷ 10))
    
    if hour_start_idx > hour_end_idx || hour_start_idx > length(timestamps)
        return ReconstructedFailure(
            timestamp,
            target_col,
            "No data available for hour $hour_start"
        )
    end
    
    hour_data = data.df[hour_start_idx:hour_end_idx, :]
    
    # Early exit: no hourly data
    if isempty(hour_data)
        return ReconstructedFailure(
            timestamp,
            target_col,
            "No data available for hour $hour_start"
        )
    end
    
    # Create profile for this target using optimized function
    profile = create_profile_for_target_optimized(hour_data, valid_sensors)
    
    if isnothing(profile)
        return ReconstructedFailure(
            timestamp,
            target_col,
            "Failed to calculate valid wind shear profile"
        )
    end
    
    # Reconstruct using the profile with optimized function
    return reconstruct_target_optimized(
        target_row,
        valid_sensors,
        target_col,
        timestamp,
        profile
    )
end

export reconstruct_single_target

# Legacy functions maintained for compatibility - REQUIRES 10-MINUTE INTERVALS
function calculate_hourly_averages(
    df::DataFrame,
    hour_start::DateTime,
    valid_sensors::Vector{SensorColumn}
)::Vector{Tuple{Float64, Float64}}
    # Validate 10-minute intervals
    if nrow(df) > 1
        interval = df.timestamp[2] - df.timestamp[1]
        if interval != Minute(10)
            error("Time series must have 10-minute intervals. Found interval: $interval. Use regularization first.")
        end
    end
    
    hour_data = df[hour_start .<= df.timestamp .< hour_start + Hour(1), :]
    return calculate_hourly_averages_optimized(hour_data, valid_sensors)
end
export calculate_hourly_averages

function create_profile_for_target(
    df::DataFrame,
    timestamp::DateTime,
    valid_sensors::Vector{SensorColumn}
)::Union{WindSpeedProfile, Nothing}
    # Validate 10-minute intervals
    if nrow(df) > 1
        interval = df.timestamp[2] - df.timestamp[1]
        if interval != Minute(10)
            error("Time series must have 10-minute intervals. Found interval: $interval. Use regularization first.")
        end
    end
    
    hour_start = floor(timestamp, Hour)
    hour_data = df[hour_start .<= df.timestamp .< hour_start + Hour(1), :]
    return create_profile_for_target_optimized(hour_data, valid_sensors)
end
export create_profile_for_target

function reconstruct_target(
    df::DataFrame,
    valid_sensors::Vector{SensorColumn},
    target_col::Symbol,
    timestamp::DateTime,
    profile::WindSpeedProfile
)::Union{ReconstructedSuccess, ReconstructedFailure}
    # Validate 10-minute intervals
    if nrow(df) > 1
        interval = df.timestamp[2] - df.timestamp[1]
        if interval != Minute(10)
            error("Time series must have 10-minute intervals. Found interval: $interval. Use regularization first.")
        end
    end
    
    # Find the target row using fast arithmetic for 10-minute intervals
    if isempty(df.timestamp)
        return ReconstructedFailure(
            timestamp,
            target_col,
            "No timestamp data available"
        )
    end
    
    start_time = df.timestamp[1]
    minutes_elapsed = Dates.value(timestamp - start_time) ÷ (1000 * 60)
    target_row_idx = (minutes_elapsed ÷ 10) + 1
    
    if target_row_idx < 1 || target_row_idx > nrow(df) || df.timestamp[target_row_idx] != timestamp
        return ReconstructedFailure(
            timestamp,
            target_col,
            "Timestamp not found in data"
        )
    end
    
    return reconstruct_target_optimized(
        df[target_row_idx, :],
        valid_sensors,
        target_col,
        timestamp,
        profile
    )
end

function find_training_pairs(ts::TimeSeriesData)::Vector{TrainingPair}
    # Get all wind speed sensors
    ws_sensors = filter(s -> 
        s.sensorType == "WindSpeed" && 
        s.statType == "avg",  # Changed from enum to string
        ts.sensors
    )
    # ... rest of function
end

end # module 