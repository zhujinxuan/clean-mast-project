module WindDirectionReconstructHourly

using DataFrames
using Statistics
using Dates
using ...Types.ReconstructSingleMast: ReconstructedSuccess, ReconstructedFailure
using ...Types.SensorColumns: SensorColumn
using ...Types.MastTimeSeries: TimeSeriesData
using ...Types.Sector: degree_diff
using ...TimeSeriesProcessing.IntervalDetection: detect_representative_interval
using ..LayerSelection: partition_training_and_targets

"""
    direction_to_vector(direction::Float64, speed::Float64=1.0)::Tuple{Float64, Float64}

Convert wind direction and speed to vector components.

# Arguments
- `direction::Float64`: Wind direction in degrees
- `speed::Float64`: Wind speed (default 1.0)

# Returns
- `Tuple{Float64, Float64}`: (x, y) vector components
"""
function direction_to_vector(direction::Float64, speed::Float64=1.0)::Tuple{Float64, Float64}
    rad = deg2rad(direction)
    return (speed * sin(rad), speed * cos(rad))
end

"""
    vector_to_direction(x::Float64, y::Float64)::Float64

Convert vector components back to direction in degrees.

# Arguments
- `x::Float64`: X component
- `y::Float64`: Y component

# Returns
- `Float64`: Direction in degrees [0, 360)
"""
function vector_to_direction(x::Float64, y::Float64)::Float64
    direction = y != 0 ? mod(rad2deg(atan(x, y)) + 360, 360) :
        x > 0 ? 90.0 : 270.0
    return direction
end

"""
    find_nearest_speed_sensor(direction_sensor::SensorColumn, sensors::Vector{SensorColumn}
                              )::Union{SensorColumn, Nothing}

Find nearest wind speed sensor for direction sensor.

# Arguments
- `direction_sensor::SensorColumn`: Direction sensor
- `sensors::Vector{SensorColumn}`: All available sensors

# Returns
- `Union{SensorColumn, Nothing}`: Nearest speed sensor or nothing
"""
function find_nearest_speed_sensor(
    direction_sensor::SensorColumn,
    sensors::Vector{SensorColumn}
)::Union{SensorColumn, Nothing}
    speed_sensors = filter(s ->
        s.sensorType == "WindSpeed" &&
        s.statType == "avg",
        sensors)

    isempty(speed_sensors) && return nothing

    nearest_idx = argmin(abs.(getfield.(speed_sensors, :height) .- direction_sensor.height))
    return speed_sensors[nearest_idx]
end

"""
    calculate_vector_average_direction(hour_data::DataFrame, direction_col::Symbol,
                                       speed_col::Union{Symbol, Nothing}
                                       )::Union{Float64, Nothing}

Calculate vector-averaged wind direction for an hour.

# Arguments
- `hour_data::DataFrame`: One hour of data
- `direction_col::Symbol`: Direction column name
- `speed_col::Union{Symbol, Nothing}`: Speed column name (optional)

# Returns
- `Union{Float64, Nothing}`: Vector-averaged direction or nothing
"""
function calculate_vector_average_direction(
    hour_data::DataFrame,
    direction_col::Symbol,
    speed_col::Union{Symbol, Nothing}
)::Union{Float64, Nothing}

    # Filter valid direction data
    valid_mask = .!ismissing.(hour_data[!, direction_col])
    if !isnothing(speed_col)
        valid_mask .&= .!ismissing.(hour_data[!, speed_col])
    end

    valid_data = hour_data[valid_mask, :]
    isempty(valid_data) && return nothing

    # Get speeds (use 1.0 if no speed sensor)
    speeds = if isnothing(speed_col)
        ones(nrow(valid_data))
    else
        valid_data[!, speed_col]
    end

    directions = valid_data[!, direction_col]

    # Calculate vector components
    rads = deg2rad.(directions)
    x_mean = mean(speeds .* sin.(rads))
    y_mean = mean(speeds .* cos.(rads))

    return vector_to_direction(x_mean, y_mean)
end

"""
    calculate_hourly_direction_difference(hour_data::DataFrame,
                                         source_sensor::SensorColumn,
                                         target_sensor::SensorColumn,
                                         all_sensors::Vector{SensorColumn}
                                         )::Union{Float64, Nothing}

Calculate mean direction difference between two layers for one hour.

Uses vector averaging with speed weighting if available.

# Arguments
- `hour_data::DataFrame`: One hour of data
- `source_sensor::SensorColumn`: Source (reference) direction sensor
- `target_sensor::SensorColumn`: Target direction sensor
- `all_sensors::Vector{SensorColumn}`: All sensors (to find speed sensors)

# Returns
- `Union{Float64, Nothing}`: Mean direction difference (target - source), or nothing
"""
function calculate_hourly_direction_difference(
    hour_data::DataFrame,
    source_sensor::SensorColumn,
    target_sensor::SensorColumn,
    all_sensors::Vector{SensorColumn}
)::Union{Float64, Nothing}

    # Find nearest speed sensors for weighting
    source_speed_sensor = find_nearest_speed_sensor(source_sensor, all_sensors)
    target_speed_sensor = find_nearest_speed_sensor(target_sensor, all_sensors)

    source_speed_col = isnothing(source_speed_sensor) ? nothing : source_speed_sensor.columnName
    target_speed_col = isnothing(target_speed_sensor) ? nothing : target_speed_sensor.columnName

    # Calculate vector averages
    source_dir = calculate_vector_average_direction(
        hour_data,
        source_sensor.columnName,
        source_speed_col
    )
    target_dir = calculate_vector_average_direction(
        hour_data,
        target_sensor.columnName,
        target_speed_col
    )

    if isnothing(source_dir) || isnothing(target_dir)
        return nothing
    end

    # Calculate shortest angle difference
    return degree_diff(target_dir, source_dir)
end

"""
    get_top_layer_direction(target_row::DataFrameRow,
                           top_layer::SensorColumn
                           )::Union{Float64, Nothing}

Get the top layer's direction at this timestamp.

# Arguments
- `target_row::DataFrameRow`: Data at specific timestamp
- `top_layer::SensorColumn`: Top layer sensor (highest)

# Returns
- `Union{Float64, Nothing}`: Top layer direction or nothing if invalid
"""
function get_top_layer_direction(
    target_row::DataFrameRow,
    top_layer::SensorColumn
)::Union{Float64, Nothing}

    dir_val = target_row[top_layer.columnName]

    # Check if valid measurement
    if !ismissing(dir_val) && dir_val >= 0 && dir_val <= 360
        return dir_val
    end

    return nothing
end

"""
    reconstruct_targets_vectorized(hour_data::DataFrame,
                                   targets::Vector{Tuple{DateTime, Symbol}},
                                   direction_profile::Dict{Float64, Float64},
                                   top_3_layers::Vector{SensorColumn}
                                   )::Vector{Union{ReconstructedSuccess, ReconstructedFailure}}

Reconstruct multiple direction targets using profile-based approach.

Always uses the top layer as reference. Direction profile maps target heights
to their mean differences from the top layer.

# Arguments
- `hour_data::DataFrame`: One hour of data
- `targets::Vector{Tuple{DateTime, Symbol}}`: List of (timestamp, column) to reconstruct
- `direction_profile::Dict{Float64, Float64}`: Map of target_height => mean_diff_from_top
- `top_3_layers::Vector{SensorColumn}`: Top 3 sensors sorted by height (descending)

# Returns
- `Vector{Union{ReconstructedSuccess, ReconstructedFailure}}`: Reconstruction results
"""
function reconstruct_targets_vectorized(
    hour_data::DataFrame,
    targets::Vector{Tuple{DateTime, Symbol}},
    direction_profile::Dict{Float64, Float64},
    top_3_layers::Vector{SensorColumn}
)::Vector{Union{ReconstructedSuccess, ReconstructedFailure}}

    isempty(targets) && return Union{ReconstructedSuccess, ReconstructedFailure}[]

    # Get top layer (always use as reference)
    top_layer = top_3_layers[1]

    # Group targets by timestamp
    targets_by_time = Dict{DateTime, Vector{Symbol}}()
    for (ts, col) in targets
        push!(get!(targets_by_time, ts, Symbol[]), col)
    end

    # Process each timestamp
    results = mapreduce(vcat, collect(targets_by_time);
        init=Union{ReconstructedSuccess, ReconstructedFailure}[]) do (ts, cols)

        row = hour_data[hour_data.timestamp .== ts, :][1, :]

        # Get top layer direction at this timestamp
        top_direction = get_top_layer_direction(row, top_layer)

        if isnothing(top_direction)
            # If top layer not available, all reconstructions fail for this timestamp
            return [ReconstructedFailure(ts, col, "Top layer direction not available at this timestamp")
                    for col in cols]
        end

        # Reconstruct all columns at this timestamp
        map(cols) do col
            # Find target height
            target_sensor_idx = findfirst(s -> s.columnName == col, top_3_layers)
            if isnothing(target_sensor_idx)
                return ReconstructedFailure(ts, col, "Target sensor not in top 3 layers")
            end
            target_height = top_3_layers[target_sensor_idx].height

            # Check if target is the top layer itself
            if target_height ≈ top_layer.height
                return ReconstructedFailure(ts, col, "Cannot reconstruct top layer using itself")
            end

            # Look up direction difference from profile
            if !haskey(direction_profile, target_height)
                return ReconstructedFailure(ts, col, "No direction difference in profile for this height")
            end

            mean_diff = direction_profile[target_height]

            # Apply direction difference from top layer
            reconstructed_direction = mod(top_direction + mean_diff, 360)

            return ReconstructedSuccess(ts, col, reconstructed_direction)
        end
    end

    return results
end

"""
    reconstruct_hourly_directions(hour_data::TimeSeriesData, representative_interval::Minute)::Vector{Union{ReconstructedSuccess, ReconstructedFailure}}

Reconstruct wind directions for one hour using top 3 layers.

Returns empty vector if fewer than 3 qualifying layers available.

# Arguments
- `hour_data::TimeSeriesData`: One hour of time series data
- `representative_interval::Minute`: The regular time interval (e.g., Minute(10))

# Returns
- `Vector{Union{ReconstructedSuccess, ReconstructedFailure}}`: Reconstruction results for this hour
"""
function reconstruct_hourly_directions(
    hour_data::TimeSeriesData,
    representative_interval::Minute
)::Vector{Union{ReconstructedSuccess, ReconstructedFailure}}

    # Filter valid wind direction sensors
    valid_sensors = filter(hour_data.sensors) do sensor
        sensor.sensorType == "WindDirection" &&
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

    # Calculate direction profile: differences from top layer to other layers
    # Profile maps target_height => mean_difference_from_top
    direction_profile = Dict{Float64, Float64}()

    # Top layer is the reference (highest)
    top_layer = top_3_layers[1]

    # Calculate differences from top layer to each other layer
    for i in 2:length(top_3_layers)
        target_sensor = top_3_layers[i]

        mean_diff = calculate_hourly_direction_difference(
            hour_data.df,
            top_layer,
            target_sensor,
            hour_data.sensors
        )

        if !isnothing(mean_diff)
            direction_profile[target_sensor.height] = mean_diff
        end
    end

    # If no direction differences calculated, fail all targets
    if isempty(direction_profile)
        return [ReconstructedFailure(ts, col, "Failed to calculate direction profile")
                for (ts, col) in targets]
    end

    # Reconstruct all targets using profile-based approach
    return reconstruct_targets_vectorized(
        hour_data.df,
        targets,
        direction_profile,
        top_3_layers
    )
end

export reconstruct_hourly_directions,
       direction_to_vector,
       vector_to_direction,
       calculate_vector_average_direction,
       calculate_hourly_direction_difference,
       get_top_layer_direction,
       reconstruct_targets_vectorized

end # module
