Notepad Name: Wind Reconstruction Refactor

Currently the wind reconstruction from mesoscale data combines training and reconstruction in one command. This creates challenges when wanting to modify training models or reuse training results. We need to split the training and reconstruction phases.

Goal: Create two distinct commands:
1. Train models using mast and mesoscale data
2. Reconstruct mast time series from mesoscale data using trained models

Core Type System:
```julia
# Abstract types for different model categories
abstract type AbstractMastReferenceModel end
abstract type AbstractMastSpeedModel <: AbstractMastReferenceModel end
abstract type AbstractMastDirectionModel <: AbstractMastReferenceModel end

# Common interface for all mast reference regression models
# Both mast and meso data must be 10-minute intervals and share timestamps
# Prerequisites:
# - Mesoscale data interpolated to 10-minute intervals
# - Mast data padded with missing values for consistent 10-minute intervals
function train(::Type{T}, params::Dict, mast::TimeSeriesData, meso::TimeSeriesData)::T where {T<:AbstractMastReferenceModel}
    error("train not implemented for model type $(T)")
end

function reconstruct(model::T, meso::TimeSeriesData)::TimeSeriesData where {T<:AbstractMastReferenceModel}
    error("reconstruct not implemented for model type $(T)")
end

# Concrete Model Types

## Direction Models
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
    DirectionOffsetModel <: AbstractMastDirectionModel

A wind direction offset model that applies constant offsets between mesoscale and mast measurements.

# Fields
- `pairs::Vector{DirectionPair}`: Vector of mast-meso sensor pairs with their offsets
"""
struct DirectionOffsetModel <: AbstractMastDirectionModel
    pairs::Vector{DirectionPair}
end

## Speed Models
"""
    SpeedSector

Parameters defining a wind speed regression model for a specific direction sector.

# Fields
- `direction_sector::DirectionSector`: The direction sector definition
- `slope::Union{Float64, Missing}`: Regression slope (k in mast_speed = k * meso_speed + b)
- `intercept::Union{Float64, Missing}`: Regression intercept (b in mast_speed = k * meso_speed + b)
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
    SectorizedRegressionModel <: AbstractMastSpeedModel

A sector-based wind speed regression model that applies different linear regressions based on wind direction sectors.

# Fields
- `pairs::Vector{SpeedPair}`: Vector of mast-meso sensor pairs with their sector-based regression parameters
- `sectors::Vector{DirectionSector}`: Common sector definitions used across all pairs
"""
struct SectorizedRegressionModel <: AbstractMastSpeedModel
    pairs::Vector{SpeedPair}
    sectors::Vector{DirectionSector}
end
```

Module Structure:

1. TimeSeriesProcessing/
   - Interpolation.jl  # Time series interpolation methods
   - Regularization.jl # Handling gaps and ensuring regular intervals
   - TimeRange.jl # Time range handling

2. WindSpeedModels/
   - SectorizedRegressionTraining.jl  # Multi-sector train implementation
   - SectorizedRegressionReconstruction.jl  # Multi-sector regression implementation

3. WindDirectionModels/
   - DirectionOffsetTraining.jl      # Constant offset train implementation
   - DirectionOffsetReconstruction.jl      # Constant offset reconstruction implementation

4. ReconstructMeso/
   - Training.jl            # Model training orchestration
   - Reconstruction.jl      # Reconstruction pipeline

Training Result File Format:
```
models/
├── windspeed/
│   ├── {model_type}/{mast_id}_{source_type}_{source_id}.jld2
│   └── e.g., 16-sectors/mast123_meso_era5.jld2
│   ├── {model_type}/{mast_id}_{source_type}_{source_id}.csv
│   └── e.g., 16-sectors/mast123_meso_era5.csv
└── winddirection/
    ├── {model_type}/{mast_id}_{source_type}_{source_id}.jld2
    └── e.g., constant-offset/mast123_meso_era5.jld2
    ├── {model_type}/{mast_id}_{source_type}_{source_id}.csv
    └── e.g., constant-offset/mast123_meso_era5.csv
```

Where:
- model_type: Identifies the specific model implementation (e.g., "sectorized", "offset")
- mast_id: Target mast identifier
- source_type: Data source type (meso, mast, etc.)
- source_id: Specific source identifier (era5, mast123, etc.)
- timestamp: Training date (YYYYMMDD)
- version: Model version for tracking iterations

Model Naming Conventions:
- Speed Models: Use descriptive names indicating the regression approach (e.g., "sectorized", "linear", "neural")
- Direction Models: Use names indicating the transformation method (e.g., "offset", "regression")

