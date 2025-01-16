module TowerShading

using DataFrames
using ..Types.CleanMastConfig: ProjectConfig
using ..Types.MastTimeSeries: TimeSeriesData, SensorColumn
using Statistics

"""
    find_nearby_sensors(sensors::Vector{SensorColumn}, target_height::Float64, max_diff::Float64=2.0)

Find all sensors at the same height or within max_diff meters of the target height.
Returns a vector of indices into the sensors array.
"""
function find_nearby_sensors(
    sensorType::String,
    sensors::Vector{SensorColumn}, 
    target_height::Float64, 
    max_diff::Float64=2.0
)::Vector{Int}
    nearby = Int[]
    for (i, sensor) in enumerate(sensors)
        if abs(sensor.height - target_height) <= max_diff && sensor.sensorType == sensorType
            push!(nearby, i)
        end
    end
    return nearby
end

"""
    get_preferred_height(heights::Vector{Float64})::Float64

Choose the preferred height from a set of nearby heights.
Prefers heights that are multiples of 10, otherwise takes the average.
"""
function get_preferred_height(heights::Vector{Float64})::Float64
    # If any height is divisible by 10, choose the closest one to the mean
    mean_height = mean(heights)
    divisible_by_10 = filter(h -> h % 10 ≈ 0, heights)
    
    if !isempty(divisible_by_10)
        return divisible_by_10[argmin(abs.(divisible_by_10 .- mean_height))]
    end
    
    # Otherwise round to nearest integer
    return round(mean_height)
end

"""
    create_merged_sensor(
        stat_sensors::Vector{SensorColumn},
        preferred_height::Float64
    )::SensorColumn

Create a new SensorColumn for merged data using the format and information from the first sensor.
"""
function create_merged_sensor(
    stat_sensors::Vector{SensorColumn},
    preferred_height::Float64
)::SensorColumn
    base_sensor = stat_sensors[1]
    
    # Create input dictionary from sensor fields
    input = Dict{String, Any}(
        "sensorType" => base_sensor.sensorType,
        "height" => preferred_height,
        "statType" => base_sensor.statType,
        "unit" => base_sensor.unit,
        "sensorDirection" => "N/A"
    )
    
    # Extract channel from original name
    m = match(r"Ch(\d+)", String(base_sensor.columnName))
    if !isnothing(m)
        input["channel"] = m.captures[1]
    end
    
    # Generate new name using format
    new_name = base_sensor.columnFormat
    for (key, value) in input
        new_name = replace(new_name, "{$key}" => (key == "height" && floor(value) == value) ? Int64(value) : value)
    end
    
    # Replace any remaining placeholders with "TS"
    new_name = replace(new_name, r"\{[^}]+\}" => "TS")
    
    return SensorColumn(
        Symbol(new_name),            # columnName
        base_sensor.columnName,      # originalColumnName (from first sensor)
        base_sensor.columnFormat,    # columnFormat
        base_sensor.sensorType,      # sensorType
        "N/A",                       # sensorDirection
        preferred_height,            # height
        base_sensor.statType,        # statType
        base_sensor.unit             # unit
    )
end

"""
    calculate_max_between_columns(df::DataFrame, cols::Vector{Symbol})::Vector{Union{Float64,Missing}}

Calculate the maximum value between corresponding elements across multiple columns,
treating missing values as non-existent rather than skipping them.
"""
function calculate_max_between_columns(df::DataFrame, cols::Vector{Symbol})::Vector{Union{Float64,Missing}}
    n_rows = nrow(df)
    result = Vector{Union{Float64,Missing}}(missing, n_rows)
    
    for i in 1:n_rows
        values = [df[i, col] for col in cols]
        non_missing = filter(!ismissing, values)
        
        result[i] = isempty(non_missing) ? missing : maximum(non_missing)
    end
    
    return result
end

"""
    merge_wind_speeds!(
        data::TimeSeriesData,
        sensors::Vector{SensorColumn},
        config::ProjectConfig
    )::Tuple{DataFrame, Vector{SensorColumn}}

Merge wind speed measurements from nearby sensors to handle tower shading.
Returns modified DataFrame and sensors list.
"""
function merge_wind_speeds!(
    data::TimeSeriesData,
    sensors::Vector{SensorColumn},
    config::ProjectConfig
)::TimeSeriesData
    # Get all unique heights for wind speed sensors
    wind_speed_sensors = filter(s -> s.sensorType == "WindSpeed", sensors)
    heights = unique(s.height for s in wind_speed_sensors)
    
    # Track columns to drop and new sensors to add
    new_sensors = copy(sensors)
    columns_to_drop = Symbol[]
    
    # Process each height
    for height in heights
        # Get all sensors at this height
        nearby_indices = find_nearby_sensors("WindSpeed", wind_speed_sensors, height)
        nearby_sensors = wind_speed_sensors[nearby_indices]
        
        # Skip if no sensors to merge
        length(nearby_sensors) <= 1 && continue
        
        preferred_height = get_preferred_height([s.height for s in nearby_sensors])
        
        # Group sensors by stat_type and merge
        for stat_type in unique([s.statType for s in nearby_sensors])
            stat_sensors = filter(s -> s.statType == stat_type && s.sensorType == "WindSpeed", nearby_sensors)
            isempty(stat_sensors) && continue
            length(stat_sensors) == 1 && continue
            
            # Create new merged sensor
            new_sensor = create_merged_sensor(stat_sensors, preferred_height)
            
            # Find all columns to drop that match height and sensorType
            cols_to_drop = [s.columnName for s in nearby_sensors]
            
            # Merge data using maximum values for existing columns
            existing_cols = [s.columnName for s in stat_sensors]
            if !isempty(existing_cols)
                data.df[!, new_sensor.columnName] = calculate_max_between_columns(data.df, existing_cols)
                push!(new_sensors, new_sensor)
                append!(columns_to_drop, cols_to_drop)
            end
        end
    end
    
    # Drop all collected columns at once
    select!(data.df, Not(unique(columns_to_drop)))
    new_sensors = filter(s -> !(s.columnName in columns_to_drop), new_sensors)
    
    # Sort new_sensors to match DataFrame column order
    df_columns = propertynames(data.df)
    new_sensors = sort(new_sensors, by=s -> findfirst(==(s.columnName), df_columns))
    
    return TimeSeriesData(data.df, new_sensors)
end

"""
    process_tower_shading(config::ProjectConfig, data::TimeSeriesData)::TimeSeriesData

Process tower shading effects in mast data by merging nearby wind speed sensors.
"""
function process_tower_shading!(
    config::ProjectConfig, 
    data::TimeSeriesData
)::TimeSeriesData
    return merge_wind_speeds!(data, data.sensors, config)
end

export process_tower_shading!

end # module