module SectorizedRegressionTraining

using DataFrames
using GLM
using Statistics
import ...Types.MastReferenceModel: train
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn, find_nearest_height_sensor
using ...Types.SpeedReferenceModel.SectorizedRegression: SectorizedRegressionModel, SpeedPair, SpeedSector, SectorizedRegressionParams
using ...Types.Sector: DirectionSector, get_direction_sector

"""
    train(::Type{SectorizedRegressionModel}, params::Dict, mast::TimeSeriesData, meso::TimeSeriesData)

Train a SectorizedRegressionModel using mast and mesoscale data.

# Arguments
- `params::Dict`: Dictionary containing:
  - `sectors::Vector{DirectionSector}`: Vector of direction sectors for the model
- `mast::TimeSeriesData`: Mast measurement data
- `meso::TimeSeriesData`: Mesoscale data interpolated to 10-minute intervals

# Returns
- `SectorizedRegressionModel`: Trained model with sector-specific regression parameters
"""
function train(::Type{SectorizedRegressionModel}, params::SectorizedRegressionParams, mast::TimeSeriesData, meso::TimeSeriesData)::SectorizedRegressionModel
    sectors = params.sectors
    
    # Find all valid speed sensor pairs
    mast_speed_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast.sensors)
    speed_pairs = Vector{SpeedPair}()
    
    for mast_sensor in mast_speed_sensors
        
        # Find nearest height meso speed sensor
        meso_speed_sensor = find_nearest_height_sensor(mast_sensor.height, meso.sensors, "WindSpeed", "avg")
        if isnothing(meso_speed_sensor)
            println("  No matching meso speed sensor found")
            continue
        end
        
        # Find highest meso direction sensor
        meso_dir_sensor = find_highest_direction_sensor(meso.sensors)
        if isnothing(meso_dir_sensor)
            println("  No meso direction sensor found")
            continue
        end
        
        # Get paired data
        paired_data = prepare_training_data(
            mast, meso,
            mast_sensor, meso_speed_sensor, meso_dir_sensor
        )
        
        # Train sector models
        sector_models = train_sector_models(paired_data, sectors)
        if isnothing(sector_models)
            println("  Failed to train sector models - insufficient data")
            continue
        end
        
        # Create SpeedPair with trained models
        push!(speed_pairs, SpeedPair(
            mast_sensor,
            meso_speed_sensor,
            meso_dir_sensor,
            sector_models
        ))
    end
    
    SectorizedRegressionModel(speed_pairs, sectors)
end

"""
Find highest wind direction sensor from available sensors
"""
function find_highest_direction_sensor(sensors::Vector{SensorColumn})::Union{SensorColumn, Nothing}
    dir_sensors = filter(s -> s.sensorType == "WindDirection" && s.statType == "avg", sensors)
    isempty(dir_sensors) && return nothing
    reduce((s1, s2) -> s1.height > s2.height ? s1 : s2, dir_sensors)
end

"""
Prepare paired training data from mast and meso measurements
"""
function prepare_training_data(
    mast::TimeSeriesData,
    meso::TimeSeriesData,
    mast_speed_sensor::SensorColumn,
    meso_speed_sensor::SensorColumn,
    meso_dir_sensor::SensorColumn
)::DataFrame
    # Get data columns
    mast_speed = mast.df[!, mast_speed_sensor.columnName]
    meso_speed = meso.df[!, meso_speed_sensor.columnName]
    meso_dir = meso.df[!, meso_dir_sensor.columnName]
    # Create DataFrame with all data
    df = DataFrame(
        mast_speed = mast_speed,
        meso_speed = meso_speed,
        meso_dir = meso_dir
    )
    # Remove rows with missing values
    dropmissing!(df)
    # Remove rows with zero or negative speeds
    df = filter(row -> row.mast_speed > 0 && row.meso_speed > 0, df)
    
    return df
end

"""
Train regression models for each sector
"""
function train_sector_models(data::DataFrame, sectors::Vector{DirectionSector})::Union{Vector{SpeedSector}, Nothing}
    data = filter(row -> !any(ismissing, row), data)
    nrow(data) < 10 && return nothing
    # Train overall model for fallback
    overall_model = lm(@formula(mast_speed ~ meso_speed), data)
    overall_coefs = coef(overall_model)

    data[:, :sector_name] = map(data.meso_dir) do dir
        if (isnothing(dir))
            return missing
        end
        s = get_direction_sector(dir, sectors)
        isnothing(s) ? missing : s.name
    end
    
    # Group and train sector models
    gdf = groupby(data, :sector_name)
    sector_models = map(sectors) do s
        # Get matching group using sector's name
        group = haskey(gdf, (s.name,)) ? gdf[(s.name,)] : nothing
        
        if !isnothing(group) && nrow(group) >= 5
            # Fit sector-specific model
            model = lm(@formula(mast_speed ~ meso_speed), group)
            coefs = coef(model)
            SpeedSector(s, coefs[2], coefs[1])
        else
            SpeedSector(s, overall_coefs[2], overall_coefs[1])
        end
    end
end


end 