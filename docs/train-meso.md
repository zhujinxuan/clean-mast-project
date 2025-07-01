# Mesoscale Model Training

## Overview

The train-meso command trains correlation models between mast and mesoscale data. These models are used later to reconstruct missing mast data using mesoscale data sources like ERA5.

## Usage

The mesoscale model training process follows a two-step approach:

### Step 1: Generate Configuration

First, generate the `train-meso.toml` configuration file:

```bash
julia bin/CleanMast.jl recommend train-meso <project-dir>
```

This command:
- Reads the existing `tower-shading.toml` configuration for mast data paths
- Reads the `parse-sensors.toml` to identify mesoscale data sources (e.g., ERA5, MERRA2)
- Creates a `train-meso.toml` file with all mast/meso combinations and model configurations

### Step 2: Execute Training

Then execute the training using the configuration:

```bash
julia bin/CleanMast.jl process train-meso <project-dir>/train-meso.toml
```

## Configuration Format

The `train-meso.toml` file specifies mast sources, mesoscale sources, and model training configurations:

```toml
# Mesoscale Model Training Configuration
# Trains correlation models between mast and mesoscale data

# Mast data sources
[[masts]]
name = "nrg-17005"
data = "./tower-shading/nrg-17005.csv"
sensors = "./tower-shading/nrg-17005.sensors.yaml"

[[masts]]
name = "nrg-17090"
data = "./tower-shading/nrg-17090.csv"
sensors = "./tower-shading/nrg-17090.sensors.yaml"

# Mesoscale data sources (shared across all masts)
[[mesos]]
name = "era5"
data = "./raw/era5.csv"
sensors = "./raw/era5.sensors.toml"

[[mesos]]
name = "merra2"
data = "./raw/merra2.csv"
sensors = "./raw/merra2.sensors.toml"

# Model training configurations
# Each model entry specifies a single training task
# All mast-meso combinations are generated automatically

# nrg-17005 with era5
[[models]]
mast_name = "nrg-17005"
meso_name = "era5"
method = "16-sector"
output = "./meso-models/nrg-17005/era5/windspeed/16-sector.jld2"

[[models]]
mast_name = "nrg-17005"
meso_name = "era5"
method = "1-sector"
output = "./meso-models/nrg-17005/era5/windspeed/1-sector.jld2"

[[models]]
mast_name = "nrg-17005"
meso_name = "era5"
method = "constant-offset"
output = "./meso-models/nrg-17005/era5/winddirection/constant-offset.jld2"

# nrg-17005 with merra2
[[models]]
mast_name = "nrg-17005"
meso_name = "merra2"
method = "16-sector"
output = "./meso-models/nrg-17005/merra2/windspeed/16-sector.jld2"

[[models]]
mast_name = "nrg-17005"
meso_name = "merra2"
method = "1-sector"
output = "./meso-models/nrg-17005/merra2/windspeed/1-sector.jld2"

[[models]]
mast_name = "nrg-17005"
meso_name = "merra2"
method = "constant-offset"
output = "./meso-models/nrg-17005/merra2/winddirection/constant-offset.jld2"

# nrg-17090 with era5
[[models]]
mast_name = "nrg-17090"
meso_name = "era5"
method = "16-sector"
output = "./meso-models/nrg-17090/era5/windspeed/16-sector.jld2"

[[models]]
mast_name = "nrg-17090"
meso_name = "era5"
method = "1-sector"
output = "./meso-models/nrg-17090/era5/windspeed/1-sector.jld2"

[[models]]
mast_name = "nrg-17090"
meso_name = "era5"
method = "constant-offset"
output = "./meso-models/nrg-17090/era5/winddirection/constant-offset.jld2"

# nrg-17090 with merra2
[[models]]
mast_name = "nrg-17090"
meso_name = "merra2"
method = "16-sector"
output = "./meso-models/nrg-17090/merra2/windspeed/16-sector.jld2"

[[models]]
mast_name = "nrg-17090"
meso_name = "merra2"
method = "1-sector"
output = "./meso-models/nrg-17090/merra2/windspeed/1-sector.jld2"

[[models]]
mast_name = "nrg-17090"
meso_name = "merra2"
method = "constant-offset"
output = "./meso-models/nrg-17090/merra2/winddirection/constant-offset.jld2"
```

## Model Types

### Wind Speed Models
- **16-sector**: Trains separate linear regression models for each of 16 wind direction sectors (22.5° each)
- **1-sector**: Trains a single linear regression model for all directions

### Wind Direction Models
- **constant-offset**: Trains a constant offset correction between mast and mesoscale wind directions

## Training Process

For each mast-meso pair, the training process:
1. Loads and aligns the time series data
2. Ensures regular 10-minute intervals for mast data
3. Interpolates mesoscale data to match mast timestamps
4. Trains the specified models
5. Saves models in JLD2 format

## Output

Models are saved to the specified paths with the following structure:
```
meso-models/
├── nrg-17005/
│   ├── era5/
│   │   ├── windspeed/
│   │   │   ├── 16-sector.jld2
│   │   │   └── 1-sector.jld2
│   │   └── winddirection/
│   │       └── constant-offset.jld2
│   └── merra2/
│       ├── windspeed/
│       │   ├── 16-sector.jld2
│       │   └── 1-sector.jld2
│       └── winddirection/
│           └── constant-offset.jld2
└── nrg-17090/
    ├── era5/
    │   ├── windspeed/
    │   │   ├── 16-sector.jld2
    │   │   └── 1-sector.jld2
    │   └── winddirection/
    │       └── constant-offset.jld2
    └── merra2/
        ├── windspeed/
        │   ├── 16-sector.jld2
        │   └── 1-sector.jld2
        └── winddirection/
            └── constant-offset.jld2
```

## Integration with Pipeline

In the full processing pipeline, mesoscale model training:
- **Requires**: Tower shading corrected mast data
- **Provides**: Trained models for mesoscale reconstruction

These models are essential for the next step (reconstruct-meso) where they're used to fill remaining gaps using mesoscale data.

## Example Workflow

```bash
# 1. Generate tower shading configuration
julia bin/CleanMast.jl recommend tower-shading my-project

# 2. Process tower shading correction
julia bin/CleanMast.jl process tower-shading my-project/tower-shading.toml

# 3. Generate mesoscale training configuration
julia bin/CleanMast.jl recommend train-meso my-project

# 4. Train mesoscale models
julia bin/CleanMast.jl process train-meso my-project/train-meso.toml
```

## Best Practices

1. **Ensure good data coverage** - Models train better with more overlapping data between mast and mesoscale
2. **Check mesoscale data quality** - Poor quality mesoscale data will produce poor models
3. **Review model statistics** - Check R² values and other metrics (if available) after training
4. **Use appropriate sector models** - 16-sector models typically perform better but require more data 