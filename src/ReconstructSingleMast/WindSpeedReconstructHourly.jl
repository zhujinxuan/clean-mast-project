module WindSpeedReconstructHourly

using DataFrames
using Statistics
using Dates
using ...Types.ReconstructSingleMast: ReconstructedSuccess, ReconstructedFailure
using ...Types.SensorColumns: SensorColumn
using ...Types.MastTimeSeries: TimeSeriesData
using ...TimeSeriesProcessing.IntervalDetection: detect_representative_interval
using ..LayerSelection: partition_training_and_targets

const MIN_SHEAR_EXPONENT = -0.25
const MAX_SHEAR_EXPONENT = 1.25

"""
    calculate_shear_exponent(heights_speeds::Vector{Tuple{Float64, Float64}},
                            reference_height::Float64)::Union{Float64, Nothing}

Calculate wind shear exponent from height-speed pairs using log-linear regression.

# Arguments
- `heights_speeds::Vector{Tuple{Float64, Float64}}`: Pairs of (height, average_speed)
- `reference_height::Float64`: Reference height for normalization

# Returns
- `Union{Float64, Nothing}`: Shear exponent clamped to valid range, or nothing if calculation fails
"""
function calculate_shear_exponent(
    heights_speeds::Vector{Tuple{Float64, Float64}},
    reference_height::Float64
)::Union{Float64, Nothing}
    length(heights_speeds) < 2 && return nothing

    # Unzip the tuples
    heights = first.(heights_speeds)
    speeds = last.(heights_speeds)

    # Calculate shear exponent using log-linear regression
    x = log.(heights ./ reference_height)
    y = log.(speeds ./ speeds[1])

    # Check for invalid values
    if any(isnan, x) || any(isnan, y) || any(isinf, x) || any(isinf, y)
        return nothing
    end

    # Simple linear regression
    x_centered = x .- mean(x)
    y_centered = y .- mean(y)

    denominator = sum(x_centered.^2)
    denominator ≈ 0.0 && return nothing

    shear_exponent = sum(x_centered .* y_centered) / denominator

    # Clamp to valid range
    return clamp(shear_exponent, MIN_SHEAR_EXPONENT, MAX_SHEAR_EXPONENT)
end

"""
    calculate_hourly_shear_exponent(hour_data::DataFrame, top_3_layers::Vector{SensorColumn}
                                   )::Union{Float64, Nothing}

Calculate shear exponent from hourly averages of top 3 layers.

# Arguments
- `hour_data::DataFrame`: One hour of data
- `top_3_layers::Vector{SensorColumn}`: Top 3 sensors sorted by height (descending)

# Returns
- `Union{Float64, Nothing}`: Shear exponent for this hour, or nothing if insufficient data
"""
function calculate_hourly_shear_exponent(
    hour_data::DataFrame,
    top_3_layers::Vector{SensorColumn}
)::Union{Float64, Nothing}

    # Calculate hourly average for each layer
    heights_speeds = Tuple{Float64, Float64}[]

    for sensor in top_3_layers
        col_data = hour_data[!, sensor.columnName]
        valid_data = filter(!ismissing, col_data)

        if !isempty(valid_data)
            mean_speed = mean(valid_data)
            if mean_speed > 0 && mean_speed <= 50
                push!(heights_speeds, (sensor.height, mean_speed))
            end
        end
    end

    # Need at least 2 layers for shear calculation
    length(heights_speeds) < 2 && return nothing

    # Use highest layer as reference
    reference_height = first(heights_speeds)[1]

    return calculate_shear_exponent(heights_speeds, reference_height)
end

"""
    apply_shear_profile(reference_speed::Float64, reference_height::Float64,
                       target_height::Float64, shear_exponent::Float64)::Float64

Apply wind shear power law to estimate speed at target height.

Formula: v_target = v_ref × (h_target / h_ref)^α

# Arguments
- `reference_speed::Float64`: Wind speed at reference height (varies per timestamp)
- `reference_height::Float64`: Reference height (highest available layer at this timestamp)
- `target_height::Float64`: Target height to reconstruct
- `shear_exponent::Float64`: Shear exponent (fixed for the hour)

# Returns
- `Float64`: Estimated wind speed at target height
"""
function apply_shear_profile(
    reference_speed::Float64,
    reference_height::Float64,
    target_height::Float64,
    shear_exponent::Float64
)::Float64
    return (target_height / reference_height)^shear_exponent * reference_speed
end

"""
    find_highest_available_reference(target_row::DataFrameRow, target_height::Float64,
                                     top_3_layers::Vector{SensorColumn}
                                     )::Union{Tuple{Float64, Float64}, Nothing}

Find the highest available layer at this timestamp to use as reference.

# Arguments
- `target_row::DataFrameRow`: Data at specific timestamp
- `target_height::Float64`: Height being reconstructed (skip this one)
- `top_3_layers::Vector{SensorColumn}`: Top 3 layers sorted by height (descending)

# Returns
- `Union{Tuple{Float64, Float64}, Nothing}`: (reference_height, reference_speed) or nothing
"""
function find_highest_available_reference(
    target_row::DataFrameRow,
    target_height::Float64,
    top_3_layers::Vector{SensorColumn}
)::Union{Tuple{Float64, Float64}, Nothing}

    # Iterate from highest to lowest
    for sensor in top_3_layers
        # Skip the target sensor itself
        if sensor.height ≈ target_height
            continue
        end

        speed_val = target_row[sensor.columnName]

        # Check if valid measurement
        if !ismissing(speed_val) && speed_val > 0 && speed_val <= 100
            return (sensor.height, speed_val)
        end
    end

    return nothing
end

"""
    reconstruct_targets_vectorized(hour_data::DataFrame,
                                   targets::Vector{Tuple{DateTime, Symbol}},
                                   shear_exponent::Float64,
                                   top_3_layers::Vector{SensorColumn}
                                   )::Vector{Union{ReconstructedSuccess, ReconstructedFailure}}

Reconstruct multiple targets using same shear exponent but timestamp-varying references.

Uses the highest available layer at each timestamp as reference.

# Arguments
- `hour_data::DataFrame`: One hour of data
- `targets::Vector{Tuple{DateTime, Symbol}}`: List of (timestamp, column) to reconstruct
- `shear_exponent::Float64`: Fixed shear exponent for this hour
- `top_3_layers::Vector{SensorColumn}`: Top 3 sensors sorted by height (descending)

# Returns
- `Vector{Union{ReconstructedSuccess, ReconstructedFailure}}`: Reconstruction results
"""
function reconstruct_targets_vectorized(
    hour_data::DataFrame,
    targets::Vector{Tuple{DateTime, Symbol}},
    shear_exponent::Float64,
    top_3_layers::Vector{SensorColumn}
)::Vector{Union{ReconstructedSuccess, ReconstructedFailure}}

    isempty(targets) && return Union{ReconstructedSuccess, ReconstructedFailure}[]

    # Group targets by timestamp for efficient processing
    targets_by_time = Dict{DateTime, Vector{Symbol}}()
    for (ts, col) in targets
        push!(get!(targets_by_time, ts, Symbol[]), col)
    end

    # Process each timestamp
    results = mapreduce(vcat, collect(targets_by_time);
        init=Union{ReconstructedSuccess, ReconstructedFailure}[]) do (ts, cols)

        row = hour_data[hour_data.timestamp .== ts, :][1, :]

        # Reconstruct all columns at this timestamp
        map(cols) do col
            # Find target height
            target_sensor_idx = findfirst(s -> s.columnName == col, top_3_layers)
            if isnothing(target_sensor_idx)
                return ReconstructedFailure(ts, col, "Target sensor not in top 3 layers")
            end
            target_height = top_3_layers[target_sensor_idx].height

            # Find highest available reference at this timestamp
            ref_result = find_highest_available_reference(row, target_height, top_3_layers)

            if isnothing(ref_result)
                return ReconstructedFailure(ts, col, "No valid reference layer at this timestamp")
            end

            reference_height, reference_speed = ref_result

            # Apply shear profile
            reconstructed = apply_shear_profile(
                reference_speed,
                reference_height,
                target_height,
                shear_exponent
            )

            # Validate result
            if isnan(reconstructed) || isinf(reconstructed) ||
               reconstructed <= 0 || reconstructed > 100
                return ReconstructedFailure(ts, col, "Reconstructed speed is invalid: $reconstructed")
            end

            return ReconstructedSuccess(ts, col, reconstructed)
        end
    end

    return results
end

"""
    reconstruct_hourly_speeds(hour_data::TimeSeriesData, representative_interval::Minute)::Vector{Union{ReconstructedSuccess, ReconstructedFailure}}

Reconstruct wind speeds for one hour using top 3 layers.

Returns empty vector if fewer than 3 qualifying layers available.

# Arguments
- `hour_data::TimeSeriesData`: One hour of time series data
- `representative_interval::Minute`: The regular time interval (e.g., Minute(10))

# Returns
- `Vector{Union{ReconstructedSuccess, ReconstructedFailure}}`: Reconstruction results for this hour
"""
function reconstruct_hourly_speeds(
    hour_data::TimeSeriesData,
    representative_interval::Minute
)::Vector{Union{ReconstructedSuccess, ReconstructedFailure}}

    # Filter valid wind speed sensors
    valid_sensors = filter(hour_data.sensors) do sensor
        sensor.sensorType == "WindSpeed" &&
        sensor.statType == "avg"
    end

    # Partition into training layers and targets
    top_3_layers, targets = partition_training_and_targets(
        hour_data.df,
        valid_sensors,
        representative_interval,
        50.0
    )

    # Skip this hour if insufficient layers
    if isnothing(top_3_layers)
        return Union{ReconstructedSuccess, ReconstructedFailure}[]
    end

    # No targets to reconstruct
    if isempty(targets)
        return Union{ReconstructedSuccess, ReconstructedFailure}[]
    end

    # Calculate shear exponent using hourly averages
    shear_exponent = calculate_hourly_shear_exponent(hour_data.df, top_3_layers)

    # If shear calculation fails, return failures for all targets
    if isnothing(shear_exponent)
        return [ReconstructedFailure(ts, col, "Failed to calculate wind shear exponent")
                for (ts, col) in targets]
    end

    # Reconstruct all targets using vectorized approach
    return reconstruct_targets_vectorized(
        hour_data.df,
        targets,
        shear_exponent,
        top_3_layers
    )
end

export reconstruct_hourly_speeds,
       calculate_shear_exponent,
       calculate_hourly_shear_exponent,
       apply_shear_profile,
       find_highest_available_reference,
       reconstruct_targets_vectorized

end # module
