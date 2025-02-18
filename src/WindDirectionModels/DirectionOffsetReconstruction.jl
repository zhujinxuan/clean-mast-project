module DirectionOffsetReconstruction

using DataFrames
using ...Types.MastTimeSeries: TimeSeriesData
import ...Types.MastReferenceModel: reconstruct
using ...Types.DirectionReferenceModel.DirectionOffset: DirectionOffsetModel

"""
    reconstruct(model::DirectionOffsetModel, meso::TimeSeriesData)::TimeSeriesData

Reconstruct mast wind direction measurements using a trained DirectionOffsetModel and mesoscale data.

# Arguments
- `model::DirectionOffsetModel`: Trained direction offset model
- `meso::TimeSeriesData`: Mesoscale data interpolated to 10-minute intervals

# Returns
- `TimeSeriesData`: Reconstructed mast measurements
"""
function reconstruct(model::DirectionOffsetModel, meso::TimeSeriesData)::TimeSeriesData
    # Create output DataFrame with same timestamps
    result_df = DataFrame(timestamp = meso.df.timestamp)
    
    # Process each direction pair
    for pair in model.pairs
        meso_dir = meso.df[!, pair.meso_sensor.columnName]
        
        # Apply offset and normalize to [0, 360)
        result_df[!, pair.mast_sensor.columnName] = map(meso_dir) do dir
            ismissing(dir) && return missing
            mod(dir + pair.offset, 360.0)
        end
    end
    
    # Create TimeSeriesData with reconstructed values
    mast_sensors = [pair.mast_sensor for pair in model.pairs]
    TimeSeriesData(result_df, mast_sensors)
end

end 