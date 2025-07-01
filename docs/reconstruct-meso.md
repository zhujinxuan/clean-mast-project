# Mesoscale Reconstruction

## Overview

The reconstruct-meso command uses trained mesoscale models to fill remaining data gaps that couldn't be filled by single-mast reconstruction. This step leverages correlation models between mast and mesoscale data (like ERA5) to provide complete time series coverage.

## Usage

The mesoscale reconstruction process follows a two-step approach:

### Step 1: Generate Configuration

First, generate the `reconstruct-meso.toml` configuration file:

```bash
julia bin/CleanMast.jl recommend reconstruct-meso <project-dir>
```

This command:
- Reads the existing `train-meso.toml` configuration to find available models
- Reads the `reconstruct-single.toml` to get mast data paths
- Creates a `reconstruct-meso.toml` file with model paths and reconstruction settings

### Step 2: Execute Reconstruction

Then execute the reconstruction using the configuration:

```bash
julia bin/CleanMast.jl process reconstruct-meso <project-dir>/reconstruct-meso.toml
```

## Configuration Format

The `reconstruct-meso.toml` file specifies reconstruction configurations:

```toml
# Mesoscale Reconstruction Configuration
# Uses trained models to fill remaining gaps with mesoscale data

# Mast configurations with embedded model specifications
[[masts]]
name = "nrg-17005"
[masts.input]
data = "./reconstruct-single/nrg-17005.csv"
sensors = "./reconstruct-single/nrg-17005.sensors.yaml"
[masts.output]
data = "./reconstruct-meso/nrg-17005.csv"
sensors = "./reconstruct-meso/nrg-17005.sensors.yaml"
[masts.time_range]
min = "2022-01-01T00:00:00"
max = "2023-12-31T23:50:00"
[masts.models.windspeed]
method = "1-sector"
meso_name = "era5"
model_file = "./meso-models/nrg-17005/era5/windspeed/1-sector.jld2"
[masts.models.winddirection]
method = "constant-offset"
meso_name = "era5"
model_file = "./meso-models/nrg-17005/era5/winddirection/constant-offset.jld2"

# Mesoscale data sources
[[meso]]
name = "era5"
[meso.input]
data = "./raw/era5.csv"
sensors = "./raw/era5.sensors.toml"

[[meso]]
name = "merra2"
[meso.input]
data = "./raw/merra2.csv"
sensors = "./raw/merra2.sensors.toml"
```

## Reconstruction Process

For each mast-meso pair, the reconstruction:
1. Loads mast data (already gap-filled by single-mast reconstruction)
2. Loads corresponding mesoscale data
3. Loads trained models (wind speed and direction)
4. Applies models to fill any remaining gaps
5. Saves the fully reconstructed time series

### Model Application

- **Wind Speed**: Uses either 1-sector or 16-sector regression models
- **Wind Direction**: Uses constant offset correction
- **Time Range**: Can be limited to specific periods if needed

## Output

The command produces:
- Reconstructed time series data in `reconstruct-meso/<mast>.csv`
- Updated sensor metadata in `reconstruct-meso/<mast>.sensors.yaml`
- Reconstruction source tracking in `process-stats/reconstruct-meso-sources-<mast>.csv`

### Source Tracking

The source tracking file records:
- Which model was used for each reconstructed point
- When reconstruction was applied
- The source data used (meso)

## Integration with Pipeline

In the full processing pipeline, mesoscale reconstruction:
- **Requires**: 
  - Single-mast reconstructed data
  - Trained mesoscale models
  - Raw mesoscale data
- **Provides**: Fully gap-filled data for representative year calibration

This step ensures complete data coverage before final calibration.

## Example Workflow

```bash
# 1. Train mesoscale models
julia bin/CleanMast.jl process train-meso my-project/train-meso.toml

# 2. Generate mesoscale reconstruction configuration
julia bin/CleanMast.jl recommend reconstruct-meso my-project

# 3. Process mesoscale reconstruction
julia bin/CleanMast.jl process reconstruct-meso my-project/reconstruct-meso.toml
```

## Best Practices

1. **Review gap statistics** - Check how many gaps remain after single-mast reconstruction
2. **Validate model quality** - Ensure models have good correlation before applying
3. **Consider time ranges** - Limit reconstruction to periods with good mesoscale data
4. **Check physical reasonableness** - Verify reconstructed values are within expected ranges 