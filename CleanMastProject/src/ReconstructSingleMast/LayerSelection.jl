module LayerSelection

using DataFrames
using Dates
using ...Types.SensorColumns: SensorColumn

"""
    select_reconstruction_layers(hour_data::DataFrame, sensors::Vector{SensorColumn},
                                 representative_interval::Minute, min_height::Float64=50.0,
                                 min_availability::Float64=0.5)::Union{Vector{SensorColumn}, Nothing}

Select top 3 layers for reconstruction that meet strict criteria.

Criteria:
- Height > 50m
- At least 50% data availability within the hour
- Must have at least 3 qualifying layers (otherwise skip reconstruction for this hour)

# Arguments
- `hour_data::DataFrame`: Data for one hour
- `sensors::Vector{SensorColumn}`: Available sensors filtered by type
- `representative_interval::Minute`: The regular interval (e.g., Minute(10))
- `min_height::Float64`: Minimum height threshold (default 50.0m)
- `min_availability::Float64`: Minimum data availability ratio (default 0.5 = 50%)

# Returns
- `Union{Vector{SensorColumn}, Nothing}`: Top 3 sensors sorted by height (descending),
  or Nothing if fewer than 3 layers meet criteria
"""
function select_reconstruction_layers(
    hour_data::DataFrame,
    sensors::Vector{SensorColumn},
    representative_interval::Minute,
    min_height::Float64=50.0,
    min_availability::Float64=0.5
)::Union{Vector{SensorColumn}, Nothing}

    # Filter sensors by height first
    eligible_sensors = filter(s -> s.height > min_height, sensors)

    # Early exit if not enough sensors
    if length(eligible_sensors) < 3
        return nothing
    end

    # Calculate data availability for each sensor
    sensor_availability = map(eligible_sensors) do sensor
        col_data = hour_data[!, sensor.columnName]
        valid_count = count(!ismissing, col_data)
        availability = valid_count / length(col_data)
        (sensor, availability)
    end

    # Filter by minimum availability (≥ 50%)
    available_sensors = [s for (s, avail) in sensor_availability if avail >= min_availability]

    # Must have at least 3 layers meeting criteria
    if length(available_sensors) < 3
        return nothing
    end

    # Sort by height descending and take top 3
    sort!(available_sensors, by = s -> s.height, rev = true)

    return available_sensors[1:3]
end

"""
    partition_training_and_targets(hour_data::DataFrame, sensors::Vector{SensorColumn},
                                   representative_interval::Minute, min_height::Float64=50.0
                                   )::Tuple{Union{Vector{SensorColumn}, Nothing}, Vector{Tuple{DateTime, Symbol}}}

Determine reconstruction targets within selected layers.

Only returns targets if we have 3 valid training layers.

# Returns
- `(training_layers, targets)`:
  - training_layers: Top 3 sensors (or nothing if insufficient)
  - targets: Vector of (timestamp, column) pairs needing reconstruction
"""
function partition_training_and_targets(
    hour_data::DataFrame,
    sensors::Vector{SensorColumn},
    representative_interval::Minute,
    min_height::Float64=50.0
)::Tuple{Union{Vector{SensorColumn}, Nothing}, Vector{Tuple{DateTime, Symbol}}}

    # Select top 3 layers with sufficient data
    top_3_layers = select_reconstruction_layers(
        hour_data,
        sensors,
        representative_interval,
        min_height,
        0.5
    )

    # If we don't have 3 layers, skip this hour entirely
    if isnothing(top_3_layers)
        return (nothing, Tuple{DateTime, Symbol}[])
    end

    # Find all missing points within these 3 layers
    targets = Tuple{DateTime, Symbol}[]

    for row in eachrow(hour_data)
        for sensor in top_3_layers
            if ismissing(row[sensor.columnName])
                push!(targets, (row.timestamp, sensor.columnName))
            end
        end
    end

    return (top_3_layers, targets)
end

export select_reconstruction_layers, partition_training_and_targets

end # module
