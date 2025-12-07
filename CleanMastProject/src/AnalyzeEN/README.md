# AnalyzeEN Module

This module provides wind data analysis functionality following EN standards for civil engineering load calculations (土建基础载荷).

## Overview

The AnalyzeEN module analyzes wind speed and direction data from measurement masts to produce:
- Mean wind speed (Vmean)
- Mean wind speed by direction sectors (15-degree bins)
- Frequency distribution by direction and wind speed

## Usage

### Command Line

```bash
julia bin/CleanMast.jl analyze en path/to/analyze-en.yaml

# Save to specific directory
julia bin/CleanMast.jl analyze en config.yaml --output results/
```

### Configuration File

Create an `analyze-en.yaml` file:

```yaml
masts:
  - name: "Mast1"
    x: 12345.67              # X coordinate
    y: 98765.43              # Y coordinate
    H: 80                    # Height for analysis (meters)
    GeoHash: "wmnrtewnzz"    # Optional location hash
    input:
      data_path: "./data.csv"         # Time series data
      sensor_path: "./sensors.yaml"   # Sensor configuration
```

## Output Format

Generates a single `WindSpeedMatrix.txt` file containing all masts with the following structure:

### 1. Header Section
```
Label = 1
X     =             431091	
Y     =              3259581	
H     =           140
GeoHash  = wmnrtewnzz
```

### 2. Wind Speed by Direction Section
```
Vmean =           5.22210
 D                      0.000000      15.000000      30.000000      ...
 V                           3.4            3.2            4.5      ...
 %                          2.27           1.13           2.18      ...
```
- `D`: Direction sectors (degrees)
- `V`: Mean wind speed in each sector (m/s)
- `%`: Frequency percentage in each sector

### 3. Frequency Matrix Section
```
    V                  0.000000      15.000000      30.000000      ...
    1           192.6          269.7          107.7      ...          71.41
    2           216.1          205.3          117.9      ...         101.18
    ...
   40            0.0            0.0            0.0      ...           0.00
```
- First column: Speed bin (1-40 m/s)
- Middle columns: Frequency by direction sector (scaled by 1000)
- Last column: All sectors frequency (scaled by 1000)

## Data Structures

### ENMastWindSpeedResult
```julia
struct ENMastWindSpeedResult
    Label::String                         # Mast identifier
    X::Float64                           # X coordinate
    Y::Float64                           # Y coordinate
    H::Int64                             # Analysis height
    GeoHash::String                      # Location hash
    Vmean::Float64                       # Mean wind speed
    VmeanByDirection::DataFrame          # Direction, Vmean, Frequency
    FrequencyByDirectionAndSpeed::DataFrame  # Direction x Speed matrix
end
```

## Implementation Details

- Direction sectors: 15-degree bins centered at 0°, 15°, 30°, ..., 345°
- Wind speed bins: 1 m/s intervals, where bin n represents speeds (n-1, n] m/s
- Missing data: Handled with Julia's `Missing` type
- Frequency scaling: Output frequencies are multiplied by 1000 (千分数) for the text format
- All directions normalized to [0, 360) range 