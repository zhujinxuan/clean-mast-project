module DirectionTraining

using DataFrames
using Statistics
using LinearAlgebra
using Dates
using ...Types.ReconstructSingleMast
using ...Types.MastTimeSeries: SensorColumn, TimeSeriesData
using ...Types.CleanMastConfig

const DEFAULT_REFERENCE_HEIGHT = 50.0

"""
Convert wind direction and speed to vector components
"""
function direction_to_vector(direction::Float64, speed::Float64=1.0)::Tuple{Float64, Float64}
    rad = deg2rad(direction)
    (speed * sin(rad), speed * cos(rad))
end
export direction_to_vector

"""
Convert vector components back to direction
"""
function vector_to_direction(x::Float64, y::Float64)::Float64
    direction = y != 0 ? mod(rad2deg(atan(x, y)) + 360, 360) : 
        x > 0 ? 90.0 : 270.0
    return direction
end
export vector_to_direction


"""
Calculate vector-averaged wind speed and direction for an hour of data
"""
function calculate_vector_average(
    data::TimeSeriesData,
    direction_sensor::SensorColumn,
    speed_sensor::Union{SensorColumn, Nothing}
)::Union{Tuple{Float64, Union{Float64, Missing}}, Nothing}
    # Get relevant columns and filter missing values
    if isnothing(speed_sensor)
        valid_data = dropmissing(data.df[!, [direction_sensor.columnName]])
    else
        valid_data = dropmissing(data.df[!, [direction_sensor.columnName, speed_sensor.columnName]])
    end
    
    isempty(valid_data) && return nothing
    
    # Get speeds vector (or ones if no speed column)
    speeds = isnothing(speed_sensor) ? ones(nrow(valid_data)) : valid_data[!, speed_sensor.columnName]
    directions = valid_data[!, direction_sensor.columnName]
    
    # Convert directions to radians and calculate components
    rads = deg2rad.(directions)
    x_mean = mean(speeds .* sin.(rads))
    y_mean = mean(speeds .* cos.(rads))
    
    # Convert back to direction
    direction = vector_to_direction(x_mean, y_mean)
    # Calculate resultant wind speed
    speed = sqrt(x_mean^2 + y_mean^2)
    
    return (direction,isnothing(speed_sensor) ? nothing : speed)
end
export calculate_vector_average

"""
Calculate mean direction difference between two heights using vector averaging
"""
function calculate_direction_correlation(
    data::TimeSeriesData,
    source_sensor::SensorColumn,
    target_sensor::SensorColumn
)::Union{Float64, Nothing}
    # Find nearest speed columns
    source_speed_sensor = find_nearest_speed_column(source_sensor, data.sensors)
    target_speed_sensor = find_nearest_speed_column(target_sensor, data.sensors)
    # Calculate vector averages
    source_vector = calculate_vector_average(data, source_sensor, source_speed_sensor)
    target_vector = calculate_vector_average(data, target_sensor, target_speed_sensor)
    if (isnothing(source_vector) || isnothing(target_vector)) 
        return nothing
    end
    
    # Calculate shortest angle difference
    diff = mod(first(target_vector) - first(source_vector) + 180, 360) - 180
    
    return diff
end

"""
Find nearest wind speed column for direction sensor
"""
function find_nearest_speed_column(
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
Filter the data to include only rows within the specified hour
"""
function filter_data_for_one_hour(data::TimeSeriesData, timestamp::DateTime)::TimeSeriesData
    hour_start = floor(timestamp, Hour)
    hour_end = hour_start + Hour(1)
    TimeSeriesData(
        filter(row -> hour_start <= row.timestamp < hour_end, data.df),
        data.sensors
    )
end

"""
Create direction correlation for a specific target column using data from a one-hour window
"""
function create_correlation_for_target(
    data::TimeSeriesData,
    target_col::Symbol,
    direction_sensors::Vector{SensorColumn},
    timestamp::DateTime
)::Union{DirectionCorrelation, Nothing}
    # Find target sensor info
    target_sensor = findfirst(s -> s.columnName == target_col, direction_sensors)
    isnothing(target_sensor) && return nothing
    
    # Filter data for one hour window
    hour_data = filter_data_for_one_hour(data, timestamp)
    
    # Find nearest sensor as reference with valid data at timestamp
    target_height = direction_sensors[target_sensor].height
    valid_references = filter(direction_sensors) do sensor
        !ismissing(hour_data.df[hour_data.df.timestamp .== timestamp, sensor.columnName][1])
    end
    
    isempty(valid_references) && return nothing
    
    reference = argmin(abs.(getfield.(valid_references, :height) .- target_height))
    source = valid_references[reference]
    
    mean_diff = calculate_direction_correlation(
        hour_data,
        source,
        target_sensor
    )
    
    isnothing(mean_diff) && return nothing
    
    return DirectionCorrelation(
        source.height,
        target_height,
        mean_diff
    )
end

"""
Reconstruct value for a single target using correlation
"""
function reconstruct_target(
    data::TimeSeriesData,
    target_col::Symbol,
    timestamp::DateTime,
    correlation::DirectionCorrelation
)::Union{ReconstructedSuccess, ReconstructedFailure}
    row = filter(r -> r.timestamp == timestamp, data.df)[1, :]
    
    # Find reference value
    reference_val = row[target_col]
    if ismissing(reference_val)
        return ReconstructedFailure(
            timestamp,
            target_col,
            "Reference measurement not available"
        )
    end
    
    reconstructed_direction = mod(reference_val + correlation.mean_difference, 360)
    
    return ReconstructedSuccess(
        timestamp,
        target_col,
        reconstructed_direction
    )
end

"""
Reconstruct missing wind directions using correlations
"""
function reconstruct_wind_directions(
    data::TimeSeriesData,
    min_height::Float64=DEFAULT_REFERENCE_HEIGHT
)::Tuple{Vector{ReconstructedSuccess}, Vector{ReconstructedFailure}}
    # Get reconstruction targets
    targets = find_reconstruction_targets(data, "WindDirection", "avg", min_height)
    
    # Get direction sensors
    direction_sensors = filter(s -> 
        s.sensorType == "WindDirection" && 
        s.statType == "avg" && 
        s.height >= min_height, 
        data.sensors)
    
    # Process each target and its columns
    results = mapreduce(vcat, targets) do target
        map(target.columns) do col
            correlation = create_correlation_for_target(
                data, 
                col, 
                direction_sensors,
                target.timestamp
            )
            
            isnothing(correlation) ? 
                ReconstructedFailure(
                    target.timestamp,
                    col,
                    "Failed to calculate valid direction correlation"
                ) :
                reconstruct_target(data, col, target.timestamp, correlation)
        end
    end
    
    # Partition results into successes and failures
    successes = filter(r -> r isa ReconstructedSuccess, results)
    failures = filter(r -> r isa ReconstructedFailure, results)
    
    return successes, failures
end

export reconstruct_wind_directions

end # module 