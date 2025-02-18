module DirectionOffsetTraining

using DataFrames
using Statistics
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn, find_nearest_height_sensor
import ...Types.MastReferenceModel: train
using ...Types.DirectionReferenceModel.DirectionOffset: DirectionOffsetModel, DirectionPair, DirectionOffsetParams
using ...Types.Sector: degree_diff

"""
    train(::Type{DirectionOffsetModel}, ::DirectionOffsetParams, mast::TimeSeriesData, meso::TimeSeriesData)

Train a DirectionOffsetModel using mast and mesoscale data.

# Arguments
- `params::Dict`: Dictionary of training parameters (unused for direction offset model)
- `mast::TimeSeriesData`: Mast measurement data
- `meso::TimeSeriesData`: Mesoscale data interpolated to 10-minute intervals

# Returns
- `DirectionOffsetModel`: Trained model with direction offsets
"""
function train(::Type{DirectionOffsetModel}, ::DirectionOffsetParams, mast::TimeSeriesData, meso::TimeSeriesData)::DirectionOffsetModel
    # Find all valid direction sensor pairs
    mast_dir_sensors = filter(s -> s.sensorType == "WindDirection" && s.statType == "avg", mast.sensors)
    direction_pairs = Vector{DirectionPair}()
    
    for mast_sensor in mast_dir_sensors
        # Find nearest height meso direction sensor
        meso_sensor = find_nearest_height_sensor(mast_sensor.height, meso.sensors, "WindDirection", "avg")
        isnothing(meso_sensor) && continue
        
        # Get paired data
        paired_data = prepare_training_data(mast, meso, mast_sensor, meso_sensor)
        
        # Calculate direction offset
        offset = calculate_direction_offset(paired_data)
        isnothing(offset) && continue
        
        # Create DirectionPair with calculated offset
        push!(direction_pairs, DirectionPair(mast_sensor, meso_sensor, offset))
    end
    
    DirectionOffsetModel(direction_pairs)
end

"""
Prepare paired training data from mast and meso measurements
"""
function prepare_training_data(
    mast::TimeSeriesData,
    meso::TimeSeriesData,
    mast_sensor::SensorColumn,
    meso_sensor::SensorColumn
)::DataFrame
    # Create DataFrame with required columns
    df = DataFrame(
        mast_dir = mast.df[!, mast_sensor.columnName],
        meso_dir = meso.df[!, meso_sensor.columnName]
    )
    
    # Filter out missing values
    filter(row -> !any(ismissing, row), df)
end

"""
Calculate mean direction offset between mast and meso measurements
"""
function calculate_direction_offset(data::DataFrame)::Union{Float64, Nothing}
    nrow(data) < 10 && return nothing
    
    # Calculate direction differences considering circular nature
    diffs = degree_diff.(data.mast_dir, data.meso_dir)
    mean(diffs)
end

end 