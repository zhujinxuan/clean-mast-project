# Representative Year Calibration

## Overview

The representative-year command calibrates wind data to a representative year using mesoscale patterns. This ensures the final dataset represents typical long-term conditions rather than being biased by the specific measurement period.

## Usage

The representative year calibration process follows a two-step approach:

### Step 1: Generate Configuration

First, generate the `representative-year.toml` configuration file:

```bash
julia bin/CleanMast.jl recommend representative-year <project-dir>
```

This command:
- Reads the existing `reconstruct-meso.toml` configuration
- Identifies available 16-sector wind speed models
- Creates a `representative-year.toml` file with calibration settings

### Step 2: Execute Calibration

Then execute the calibration using the configuration:

```bash
julia bin/CleanMast.jl process representative-year <project-dir>/representative-year.toml
```

## Configuration Format

The `representative-year.toml` file specifies calibration configurations:

```toml
# Representative Year Calibration Configuration
# Calibrates data to a representative year using mesoscale patterns

# Mast configurations for calibration
# Note: Uses 16-sector windspeed model for directional calibration
[[masts]]
name = "nrg-17005"
[masts.input]
data = "./reconstruct-meso/nrg-17005.csv"
sensors = "./reconstruct-meso/nrg-17005.sensors.yaml"
[masts.output]
data = "./representative-year/nrg-17005.csv"
sensors = "./representative-year/nrg-17005.sensors.yaml"
[masts.time_range]
min = "2022-01-01T00:00:00"
max = "2023-12-31T23:50:00"
[masts.models.windspeed]
method = "16-sector"
meso_name = "era5"
model_file = "./meso-models/nrg-17005/era5/windspeed/16-sector.jld2"

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

## Calibration Method

The calibration process:

1. **Analyzes mesoscale data** to find a representative year
   - Calculates mean wind speed for the full mesoscale period
   - Identifies years where mean speed matches long-term average

2. **Calculates directional adjustments**
   - Uses 16 wind direction sectors
   - Computes speed differences between training period and representative year
   - Applies sector-specific calibration factors

3. **Applies calibration**
   - Adjusts wind speeds based on direction and calibration factors
   - Preserves data patterns while correcting for period bias

## Why 16-Sector Model?

The representative year calibration specifically uses the 16-sector wind speed model because:
- It provides direction-dependent calibration
- Different wind directions may have different biases
- Ensures accurate representation of directional wind patterns

## Output

The command produces:
- Calibrated time series data in `representative-year/<mast>.csv`
- Updated sensor metadata in `representative-year/<mast>.sensors.yaml`
- Calibration information in `process-stats/representative-year-info-<mast>.yaml`

### Calibration Info

The calibration info file contains:
- Reference year start date
- Whether calibration was applied
- Number of sensors calibrated

## Integration with Pipeline

In the full processing pipeline, representative year calibration:
- **Requires**: 
  - Fully reconstructed mast data (from reconstruct-meso)
  - Mesoscale data for long-term reference
  - 16-sector wind speed model
- **Provides**: Final calibrated dataset ready for wind resource assessment

This is typically the final data processing step before analysis.

## Example Workflow

```bash
# 1. Complete mesoscale reconstruction
julia bin/CleanMast.jl process reconstruct-meso my-project/reconstruct-meso.toml

# 2. Generate representative year configuration
julia bin/CleanMast.jl recommend representative-year my-project

# 3. Process representative year calibration
julia bin/CleanMast.jl process representative-year my-project/representative-year.toml
```

## Best Practices

1. **Ensure sufficient mesoscale history** - Need multiple years for reliable calibration
2. **Review calibration factors** - Large adjustments may indicate data quality issues
3. **Validate against independent data** - Compare with nearby long-term stations if available
4. **Document training period** - The period used affects calibration results 