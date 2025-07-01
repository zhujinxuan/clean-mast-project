module DirectionTraining

using DataFrames
using Statistics
using LinearAlgebra
using Dates
using ...Types.ReconstructSingleMast
using ...Types.MastTimeSeries: SensorColumn, TimeSeriesData
using ...Types.Sector: degree_diff

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
Get speeds for vector averaging, handling missing values
Returns a vector of speeds with missing values replaced by mean or default value
"""
function get_speeds_for_averaging(
    data::AbstractDataFrame,
    speed_sensor::Union{SensorColumn, Nothing}
)::Vector{Float64}
    if isnothing(speed_sensor)
        return ones(nrow(data))
    end
    
    # Get speeds and handle missing values
    speed_col = Symbol(speed_sensor.columnName)  # Convert string column name to symbol
    raw_speeds = data[!, speed_col]
    if all(ismissing, raw_speeds)
        return ones(nrow(data))  # If all speeds missing, use 1.0
    end
    
    # Replace missing speeds with mean of available speeds
    valid_speeds = filter(!ismissing, raw_speeds)
    mean_speed = mean(valid_speeds)
    return map(s -> ismissing(s) ? mean_speed : s, raw_speeds)
end
export get_speeds_for_averaging

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
    # Get relevant columns and filter missing direction values
    columns = isnothing(speed_sensor) ? 
        [direction_sensor.columnName] : 
        [direction_sensor.columnName, speed_sensor.columnName]
    valid_data = dropmissing(data.df[!, columns])
    
    isempty(valid_data) && return nothing
    
    # Get speeds with missing values handled
    speeds = get_speeds_for_averaging(valid_data, speed_sensor)
    directions = valid_data[!, direction_sensor.columnName]
    
    # Convert directions to radians and calculate components
    rads = deg2rad.(directions)
    x_mean = mean(speeds .* sin.(rads))
    y_mean = mean(speeds .* cos.(rads))
    
    # Convert back to direction
    direction = vector_to_direction(x_mean, y_mean)
    # Calculate resultant wind speed
    speed = sqrt(x_mean^2 + y_mean^2)
    
    return (direction, isnothing(speed_sensor) ? missing : speed)
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
    diff = degree_diff(first(target_vector), first(source_vector))
    
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
Calculate time-mean direction difference between two heights
"""
function calculate_time_mean_direction_diff(
    data::TimeSeriesData,
    lower_height::Float64,
    upper_height::Float64
)::Union{Float64, Nothing}
    # Find sensors at specified heights
    lower_sensor = findfirst(s -> 
        s.sensorType == "WindDirection" && 
        s.statType == "avg" && 
        s.height ≈ lower_height, 
        data.sensors)
    upper_sensor = findfirst(s -> 
        s.sensorType == "WindDirection" && 
        s.statType == "avg" && 
        s.height ≈ upper_height, 
        data.sensors)
    
    isnothing(lower_sensor) && return nothing
    isnothing(upper_sensor) && return nothing
    
    # Get all valid pairs of measurements
    valid_rows = filter(eachrow(data.df)) do row
        !ismissing(row[data.sensors[lower_sensor].columnName]) && 
        !ismissing(row[data.sensors[upper_sensor].columnName])
    end
    
    isempty(valid_rows) && return nothing
    
    # Calculate mean direction difference
    diffs = map(valid_rows) do row
        degree_diff(
            row[data.sensors[upper_sensor].columnName],
            row[data.sensors[lower_sensor].columnName]
        )
    end
    
    mean(diffs)
end

"""
Create direction correlation for target with fallback to time-mean difference
"""
function create_correlation_for_target(
    data::TimeSeriesData,
    target_col::Symbol,
    direction_sensors::Vector{SensorColumn},
    timestamp::DateTime
)::Union{DirectionCorrelation, Nothing}
    # Get target sensor
    target_sensor = findfirst(s -> s.columnName == target_col, data.sensors)
    isnothing(target_sensor) && return nothing
    target_height = data.sensors[target_sensor].height
    
    # Get data for this hour (use full hour instead of single timestamp)
    hour_start = floor(timestamp, Hour)
    hour_data = TimeSeriesData(
        filter(r -> hour_start <= r.timestamp < hour_start + Hour(1), data.df),
        data.sensors
    )
    
    # Filter out the target sensor from potential reference sensors
    reference_sensors = filter(s -> s.columnName != target_col, direction_sensors)
    
    # Find nearest valid reference sensor with data in this hour
    nearest_reference = reduce(reference_sensors, init=nothing) do best_so_far, sensor
        # Check if sensor has any valid data in this hour
        has_valid_data = any(!ismissing, hour_data.df[:, sensor.columnName])
        !has_valid_data && return best_so_far
        
        # If first valid sensor, use it
        isnothing(best_so_far) && return sensor
        
        # Keep sensor with height closest to target
        abs(sensor.height - target_height) < abs(best_so_far.height - target_height) ? sensor : best_so_far
    end
    
    if !isnothing(nearest_reference)
        mean_diff = calculate_direction_correlation(
            hour_data,
            nearest_reference,
            data.sensors[target_sensor]
        )
        
        !isnothing(mean_diff) && return DirectionCorrelation(
            nearest_reference.height,
            target_height,
            mean_diff
        )
    end
    
    # If direct correlation fails, try using time-mean difference with nearest height
    sorted_heights = sort(unique([s.height for s in direction_sensors]))
    target_idx = searchsortedfirst(sorted_heights, target_height)
    
    if target_idx > 1  # Try lower height first
        time_mean_diff = calculate_time_mean_direction_diff(data, sorted_heights[target_idx-1], target_height)
        if !isnothing(time_mean_diff)
            return DirectionCorrelation(
                sorted_heights[target_idx-1],
                target_height,
                time_mean_diff
            )
        end
    end
    
    if target_idx <= length(sorted_heights)  # Then try higher height
        time_mean_diff = calculate_time_mean_direction_diff(data, target_height, sorted_heights[target_idx])
        if !isnothing(time_mean_diff)
            return DirectionCorrelation(
                sorted_heights[target_idx],
                target_height,
                -time_mean_diff  # Negate since we're using higher height as reference
            )
        end
    end
    
    return nothing
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
    
    reference_sensor = begin
        idx = findfirst(s -> s.statType == "avg" && s.sensorType == "WindDirection" && s.height == correlation.source_height, data.sensors)
        isnothing(idx) ? nothing : data.sensors[idx]
    end

    # Find reference value
    reference_val = row[reference_sensor.columnName]
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
    if isempty(targets)
        return ([], [])
    end
    
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