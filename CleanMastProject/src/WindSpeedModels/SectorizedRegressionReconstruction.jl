module SectorizedRegressionReconstruction

using DataFrames
using ...Types.MastTimeSeries: TimeSeriesData
import ...Types.MastReferenceModel: reconstruct
using ...Types.Sector: get_direction_sector
using ...Types.SpeedReferenceModel.SectorizedRegression: SectorizedRegressionModel, SpeedSector

"""
    reconstruct(model::SectorizedRegressionModel, meso::TimeSeriesData)::TimeSeriesData

Reconstruct mast wind speed measurements using a trained SectorizedRegressionModel and mesoscale data.

# Arguments
- `model::SectorizedRegressionModel`: Trained sector-based regression model
- `meso::TimeSeriesData`: Mesoscale data interpolated to 10-minute intervals

# Returns
- `TimeSeriesData`: Reconstructed mast measurements
"""
function reconstruct(model::SectorizedRegressionModel, meso::TimeSeriesData)::TimeSeriesData
    # Create output DataFrame with same timestamps
    result_df = DataFrame(timestamp = meso.df.timestamp)
    
    # Process each speed pair
    for pair in model.pairs
        meso_speed = meso.df[!, pair.meso_speed_sensor.columnName]
        meso_dir = meso.df[!, pair.meso_direction_sensor.columnName]
        
        # Apply sector models
        result_df[!, pair.mast_speed_sensor.columnName] = map(zip(meso_speed, meso_dir)) do (speed, dir)
            if ismissing(speed) || ismissing(dir)
                return missing
            end
            
            # Find appropriate sector model
            sector_model = get_sector_model(dir, pair.sectors)
            if isnothing(sector_model)
                return missing
            end
            
            # Apply regression with bounds
            reconstructed = speed * sector_model.slope + sector_model.intercept
            clamp(reconstructed, 0.5, 25.0)
        end
    end
    
    # Create TimeSeriesData with reconstructed values
    mast_sensors = [pair.mast_speed_sensor for pair in model.pairs]
    TimeSeriesData(result_df, mast_sensors)
end

"""
Get the appropriate sector model for a given direction
"""
function get_sector_model(direction::Float64, sectors::Vector{SpeedSector})::Union{SpeedSector, Nothing}
    sector = get_direction_sector(direction, map(s -> s.direction_sector, sectors))
    if isnothing(sector)
        return nothing
    end

    idx = findfirst(s -> s.direction_sector.center == sector.center, sectors)
    isnothing(idx) ? nothing : sectors[idx]
end


end 