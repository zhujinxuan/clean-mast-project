"""
    DirectionOffset.jl

Module for wind direction offset modeling between mesoscale and mast measurements.
This implementation calculates constant direction offsets between meso and mast sensors.
"""
module DirectionOffset

import ...MastReferenceModel: AbstractDirectionReferenceModel, getModelName
using ...MastTimeSeries: TimeSeriesData, SensorColumn
import ...Utils: show_as_dataframe
using DataFrames
using Statistics

export DirectionOffsetModel, DirectionPair, DirectionOffsetParams, DirectionOffsetModelName, getModelName

"""
    DirectionPair

Represents a paired relationship between a mast sensor and mesoscale sensor with their direction offset.

# Fields
- `mast_sensor::SensorColumn`: Reference mast wind direction sensor
- `meso_sensor::SensorColumn`: Mesoscale wind direction data source
- `offset::Float64`: Direction offset value in degrees to add to mesoscale direction
"""
struct DirectionPair
    mast_sensor::SensorColumn
    meso_sensor::SensorColumn
    offset::Float64
end

"""
    DirectionOffsetModel <: AbstractDirectionReferenceModel

A wind direction offset model that applies constant offsets between mesoscale and mast measurements.

# Fields
- `pairs::Vector{DirectionPair}`: Vector of mast-meso sensor pairs with their offsets
"""
struct DirectionOffsetModel <: AbstractDirectionReferenceModel
    pairs::Vector{DirectionPair}
end

function show_as_dataframe(model::DirectionOffsetModel) :: DataFrame
    df = DataFrame(
        mast_sensor = [pair.mast_sensor.columnName for pair in model.pairs],
        meso_sensor = [pair.meso_sensor.columnName for pair in model.pairs],
        offset = [pair.offset for pair in model.pairs]
    )
    df
end

struct DirectionOffsetParams
end

const DirectionOffsetModelName = "constant-direction-offset"
function getModelName(::DirectionOffsetModel)::String
    return DirectionOffsetModelName
end

end # module 