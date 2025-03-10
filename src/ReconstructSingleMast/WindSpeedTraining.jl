module WindSpeedTraining

using DataFrames
using Statistics
using Dates
using ...Types.ReconstructSingleMast
using ...Types.MastTimeSeries: SensorColumn, TimeSeriesData
using ...MastTimeSeries
using ...Types.CleanMastConfig

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
    
    # Simple linear regression to find shear exponent
    shear_exponent = sum((x .- mean(x)) .* (y .- mean(y))) / sum((x .- mean(x)).^2)
    
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
Calculate hourly average for wind speeds, handling missing values
"""
function calculate_hourly_averages(
    df::DataFrame,
    hour_start::DateTime,
    valid_sensors::Vector{SensorColumn}
)::Vector{Tuple{Float64, Float64}}
    hour_data = df[hour_start .<= df.timestamp .< hour_start + Hour(1), :]
    
    # Extract heights and speeds using functional approach
    sensor_data = filter(sensor -> !isempty(filter(!ismissing, hour_data[:, sensor.columnName])), valid_sensors)
    heights_speeds = map(sensor -> (
        sensor.height,
        mean(filter(!ismissing, hour_data[:, sensor.columnName]))
    ), sensor_data)
    
    return heights_speeds
end
export calculate_hourly_averages

"""
Create wind shear profile for a specific timestamp
"""
function create_profile_for_target(
    df::DataFrame,
    timestamp::DateTime,
    valid_sensors::Vector{SensorColumn}
)::Union{WindSpeedProfile, Nothing}
    hour_start = floor(timestamp, Hour)
    heights_speeds = calculate_hourly_averages(df, hour_start, valid_sensors)
    
    length(heights_speeds) < 2 && return nothing
    return calculate_wind_shear_profile(heights_speeds)
end
export create_profile_for_target

"""
Reconstruct value for a single target using a profile
"""
function reconstruct_target(
    df::DataFrame,
    valid_sensors::Vector{SensorColumn},
    target_col::Symbol,
    timestamp::DateTime,
    profile::WindSpeedProfile
)::Union{ReconstructedSuccess, ReconstructedFailure}
    sensor = first(filter(s -> s.columnName == target_col, valid_sensors))
    
    # Get the row for this specific timestamp
    row = df[df.timestamp .== timestamp, :]
    isempty(row) && return ReconstructedFailure(
        timestamp,
        target_col,
        "Timestamp not found in data"
    )

    # Find valid speed measurements at this exact timestamp
    valid_speeds = [(s.height, row[1, s.columnName])
        for s in valid_sensors
        if !ismissing(row[1, s.columnName])]
    
    isempty(valid_speeds) && return ReconstructedFailure(
        timestamp,
        target_col,
        "No valid reference measurements found"
    )
    
    # Find nearest height with valid measurement
    reference_height, reference_speed = reduce(valid_speeds; init=first(valid_speeds)) do closest, current
        abs(closest[1] - sensor.height) < abs(current[1] - sensor.height) ? closest : current
    end
    
    reconstructed_speed = apply_wind_shear_profile(
        WindSpeedProfile(reference_height, profile.shear_exponent),
        reference_speed,
        sensor.height
    )
    
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