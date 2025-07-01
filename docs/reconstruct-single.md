# Single Mast Reconstruction

## Overview

The single mast reconstruction command fills data gaps using correlations between sensors on the same mast. This is particularly useful for filling gaps when one sensor on a mast fails but other sensors continue to record data.

## Usage

The single mast reconstruction process follows a two-step approach:

### Step 1: Generate Configuration

First, generate the `reconstruct-single.toml` configuration file:

```bash
julia bin/CleanMast.jl recommend reconstruct-single <project-dir>
```

This command:
- Reads the existing `tower-shading.toml` configuration
- Creates a `reconstruct-single.toml` file with appropriate input/output paths

### Step 2: Execute Reconstruction

Then execute the reconstruction using the configuration:

```bash
julia bin/CleanMast.jl process reconstruct-single <project-dir>/reconstruct-single.toml
```

## Configuration Format

The `reconstruct-single.toml` file specifies input and output paths for each mast:

```toml
# Single Mast Reconstruction Configuration
# Fills gaps using correlations between sensors on the same mast

[[masts]]
name = "nrg-17005"
[masts.input]
data = "./tower-shading/nrg-17005.csv"
sensors = "./tower-shading/nrg-17005.sensors.yaml"
[masts.output]
data = "./reconstruct-single/nrg-17005.csv"
sensors = "./reconstruct-single/nrg-17005.sensors.yaml"

[[masts]]
name = "nrg-17090"
[masts.input]
data = "./tower-shading/nrg-17090.csv"
sensors = "./tower-shading/nrg-17090.sensors.yaml"
[masts.output]
data = "./reconstruct-single/nrg-17090.csv"
sensors = "./reconstruct-single/nrg-17090.sensors.yaml"
```

## Reconstruction Method

The single mast reconstruction uses:
- **Wind Speed**: Linear regression between different height measurements on the same mast
- **Wind Direction**: Direction offset calibration between different height measurements

The reconstruction process:
1. Identifies missing data points in each sensor
2. Searches for correlations with other sensors on the same mast
3. Applies the best available model to fill gaps
4. Validates reconstructed values for physical reasonableness

## Output

The command produces:
- Reconstructed time series data in `reconstruct-single/<mast>.csv`
- Updated sensor metadata in `reconstruct-single/<mast>.sensors.yaml`
- Reconstruction statistics in `process-stats/reconstruct-single-<mast>.yaml`

### Statistics File

The statistics file contains:
- `successes`: List of successfully reconstructed data points with timestamp, column, and value
- `failures`: List of failed reconstruction attempts with timestamp, column, and reason

## Integration with Pipeline

In the full processing pipeline, single mast reconstruction:
- **Requires**: Tower shading corrected data
- **Provides**: Gap-filled data for mesoscale model training

This step is essential before training mesoscale models as it maximizes the available training data.

## Example Workflow

```bash
# 1. Generate tower shading configuration
julia bin/CleanMast.jl recommend tower-shading my-project

# 2. Process tower shading
julia bin/CleanMast.jl process tower-shading my-project/tower-shading.toml

# 3. Generate single mast reconstruction configuration
julia bin/CleanMast.jl recommend reconstruct-single my-project

# 4. Process single mast reconstruction
julia bin/CleanMast.jl process reconstruct-single my-project/reconstruct-single.toml
```

## Best Practices

1. **Review reconstruction statistics** - Check the success rate and failure reasons
2. **Validate reconstructed data** - Ensure physical reasonableness of filled values
3. **Consider sensor quality** - Reconstruction quality depends on correlation between sensors
4. **Check coverage improvement** - Compare data coverage before and after reconstruction 