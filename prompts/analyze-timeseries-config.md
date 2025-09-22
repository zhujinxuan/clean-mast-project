# Analyze Timeseries Configuration Guide

## Overview

This guide explains how to create configuration files for the `analyze timeseries` command, which performs comprehensive wind data analysis including turbulence intensity, wind roses, vertical profiles, and statistical analysis.

## Configuration File Structure

The analyze configuration supports TOML, YAML, and JSON formats. Here's the complete structure:

### TOML Format

```toml
# Optional: Minimum height threshold for turbulence intensity plotting
# Default behavior: 120m if highest sensor >= 120m, otherwise second highest sensor height
min_plot_height = 100.0

# Mast configurations (can have multiple masts)
[[masts]]
name = "mast-name"
[masts.input]
data = "path/to/timeseries.csv"           # Time series data file
sensors = "path/to/sensors.toml"          # Sensor configuration file
[masts.airDensity]
density = 1.225                           # Air density (kg/m³)
reference_height = 80.0                   # Reference height for air density

# Output configuration
[output]
path = "analyze-results"                  # Output directory (relative to config file)
```

### YAML Format

```yaml
# Optional: Minimum height threshold for turbulence intensity plotting
min_plot_height: 100.0

masts:
  - name: "mast-name"
    input:
      data: "path/to/timeseries.csv"
      sensors: "path/to/sensors.toml"
    airDensity:
      density: 1.225
      reference_height: 80.0

output:
  path: "analyze-results"
```

## Min Plot Height Configuration

The `min_plot_height` parameter controls which sensor heights are included in turbulence intensity plots and analysis.

### Recommended Logic

**If highest wind speed sensor height >= 120m:**
- Set `min_plot_height = 120.0`
- This follows industry standards for wind energy applications

**If highest wind speed sensor height < 120m:**
- Set `min_plot_height` to the **second highest** sensor height
- This ensures meaningful comparative analysis between multiple heights

### Examples

#### Case 1: High Tower (sensors at 40m, 80m, 120m, 140m)
```toml
min_plot_height = 120.0  # Use standard 120m threshold
```

#### Case 2: Medium Tower (sensors at 30m, 60m, 80m, 100m)
```toml
min_plot_height = 80.0   # Use second highest (80m), exclude only 100m
```

#### Case 3: Low Tower (sensors at 20m, 40m, 60m)
```toml
min_plot_height = 40.0   # Use second highest (40m), exclude only 60m
```

#### Case 4: Real Example - Lubei Project (sensors at 38.5m, 58.5m, 78.5m, 89.5m)
```toml
min_plot_height = 78.5   # Use second highest (78.5m), highest is 89.5m < 120m
```

## Complete Configuration Examples

### Single Mast Analysis

```toml
# analyze-single.toml
min_plot_height = 120.0

[[masts]]
name = "NRG-Tower-01"
[masts.input]
data = "raw/nrg-tower-01.csv"
sensors = "raw/nrg-tower-01.sensors.toml"
[masts.airDensity]
density = 1.225
reference_height = 120.0

[output]
path = "analyze-results"
```

### Multi-Mast Analysis

```toml
# analyze-multi.toml
min_plot_height = 100.0

[[masts]]
name = "Mast-A"
[masts.input]
data = "raw/mast-a.csv"
sensors = "raw/mast-a.sensors.toml"
[masts.airDensity]
density = 1.220
reference_height = 100.0

[[masts]]
name = "Mast-B"
[masts.input]
data = "raw/mast-b.csv"
sensors = "raw/mast-b.sensors.toml"
[masts.airDensity]
density = 1.230
reference_height = 120.0

[output]
path = "multi-mast-analysis"
```

## Field Descriptions

### Required Fields

- **`masts`**: Array of mast configurations
- **`masts.name`**: Unique identifier for the mast
- **`masts.input.data`**: Path to CSV time series data file
- **`masts.input.sensors`**: Path to sensor configuration file
- **`output.path`**: Directory for analysis results

### Optional Fields

- **`min_plot_height`**: Minimum height for turbulence intensity plotting (default: 120.0)
- **`masts.airDensity`**: Air density configuration for power calculations
  - **`density`**: Air density in kg/m³ (default: 1.225)
  - **`reference_height`**: Reference height for density calculation

## Usage

```bash
# Run analysis with TOML configuration
julia bin/CleanMast.jl analyze timeseries analyze-config.toml

# Run analysis with YAML configuration  
julia bin/CleanMast.jl analyze timeseries analyze-config.yaml

# Run analysis with JSON configuration
julia bin/CleanMast.jl analyze timeseries analyze-config.json
```

## Generated Outputs

The analysis creates comprehensive results including:

- **Turbulence Intensity**: IEC standard comparisons, sector analysis
- **Wind Roses**: Frequency and power distribution plots
- **Vertical Profiles**: Wind shear and speed ratios
- **Temporal Analysis**: Daily/monthly patterns
- **Statistical Reports**: Weibull distributions, extreme wind analysis
- **Typst Reports**: Professional documentation in Chinese/English

## Path Resolution

All paths in the configuration are resolved relative to the configuration file location:

```toml
# If analyze-config.toml is in /project/configs/
[masts.input]
data = "../raw/data.csv"        # Resolves to /project/raw/data.csv
sensors = "../raw/sensors.toml" # Resolves to /project/raw/sensors.toml

[output]
path = "../results"             # Resolves to /project/results
```
