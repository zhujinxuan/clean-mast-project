"""
    SectorizedRegression.jl

Module for sector-based wind speed regression modeling between mesoscale and mast measurements.
This implementation uses linear regression within defined wind direction sectors.
"""
module SectorizedRegression

using ...Types.MastTimeSeries: TimeSeriesData
using ...Types.SensorColumns: SensorColumn
import ...Utils: show_as_dataframe
using ...Sector: DirectionSector
import ...MastReferenceModel: AbstractSpeedReferenceModel,getModelName
using DataFrames
using Statistics

export SectorizedRegressionModel, SpeedSector, SpeedPair

"""
    SpeedSector

Parameters defining a wind speed regression model for a specific direction sector.

# Fields
- `direction_sector::DirectionSector`: The direction sector definition
- `slope::Float64`: Regression slope (k in mast_speed = k * meso_speed + b)
- `intercept::Float64`: Regression intercept (b in mast_speed = k * meso_speed + b)
"""
struct SpeedSector
    direction_sector::DirectionSector
    slope::Union{Float64, Missing}
    intercept::Union{Float64, Missing}
end

"""
    SpeedPair

Represents a paired relationship between mast and mesoscale sensors with sector-based regression parameters.

# Fields
- `mast_speed_sensor::SensorColumn`: Reference mast wind speed sensor
- `meso_speed_sensor::SensorColumn`: Mesoscale wind speed data source
- `meso_direction_sensor::SensorColumn`: Mesoscale wind direction data source (for sector determination)
- `sectors::Vector{SpeedSector}`: Vector of sector-specific regression parameters
"""
struct SpeedPair
    mast_speed_sensor::SensorColumn
    meso_speed_sensor::SensorColumn
    meso_direction_sensor::SensorColumn
    sectors::Vector{SpeedSector}
end

"""
    SectorizedRegressionModel <: AbstractSpeedReferenceModel

A sector-based wind speed regression model that applies different linear regressions based on wind direction sectors.

# Fields
- `pairs::Vector{SpeedPair}`: Vector of mast-meso sensor pairs with their sector-based regression parameters
"""
struct SectorizedRegressionModel <: AbstractSpeedReferenceModel
    pairs::Vector{SpeedPair}
    sectors::Vector{DirectionSector}
end
struct SectorizedRegressionParams
    sectors::Vector{DirectionSector}
end

function find_pair_from_mast_sensor(model::SectorizedRegressionModel, mast_speed_sensor::SensorColumn) :: Union{SpeedPair, Nothing}
    idx = findfirst(p -> p.mast_speed_sensor == mast_speed_sensor, model.pairs)
    if isnothing(idx)
        return nothing
    end
    model.pairs[idx]
end
export find_pair_from_mast_sensor

# map df.pairs to each pair's show_as_dataframe
# combine the results into a single dataframe
function show_as_dataframe(model::SectorizedRegressionModel) :: DataFrame 
    # Create DataFrame for each pair and explicitly collect into Vector{DataFrame}
    dataframes = DataFrame[show_as_dataframe(pair) for pair in model.pairs]
    
    # If no pairs, return empty DataFrame with correct structure
    if isempty(dataframes)
        return DataFrame(
            direction_sector = String[],
            slope = Float64[],
            intercept = Float64[],
            mast_speed_sensor = String[],
            meso_speed_sensor = String[],
            meso_direction_sensor = String[]
        )
    end
    
    # Combine all DataFrames
    vcat(dataframes...)
end

function show_as_dataframe(pair::SpeedPair) :: DataFrame
    # map pair.sectors to each sector's show_as_dataframe
    # combine the results into a single dataframe and append other column names
    df = DataFrame(
        direction_sector = [sector.direction_sector.name for sector in pair.sectors],
        slope = [sector.slope for sector in pair.sectors],
        intercept = [sector.intercept for sector in pair.sectors],
    )
    df = hcat(df, DataFrame(
        mast_speed_sensor = fill(pair.mast_speed_sensor.columnName, nrow(df)),
        meso_speed_sensor = fill(pair.meso_speed_sensor.columnName, nrow(df)),
        meso_direction_sensor = fill(pair.meso_direction_sensor.columnName, nrow(df)),
    ))
    df
end

function getModelName(model ::SectorizedRegressionModel)::String
    return "$(length(model.sectors))-sector"
end

end # module 