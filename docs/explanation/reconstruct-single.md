# Single Mast Reconstruction

This document describes the methodology used for reconstructing missing wind measurements in a single meteorological mast dataset.

## Overview

Single mast reconstruction is used to fill gaps in wind measurements using data from other heights on the same mast. The process handles both wind speed and wind direction separately, using appropriate physical and statistical methods for each.

## Physical Assumptions

The reconstruction methodology is based on several key physical assumptions:

1. **Temporal Stability**: 
   - The wind shear profile (both direction and speed) is assumed to be nearly constant within each hour
   - This assumption allows us to use measurements from the same hour for direct reconstruction

2. **Profile Continuity**:
   - When hourly profiles cannot be calculated (due to missing data), we fall back to time-averaged profiles
   - This assumes that the long-term average profile is representative enough for reconstruction
   - The time-averaged profile serves as a trained parameter that captures the site's typical wind behavior

3. **Vertical Coherence**:
   - Wind characteristics at different heights are physically correlated
   - This correlation becomes stronger for measurements closer in height
   - While hourly wind patterns may vary significantly, the average relationship between measurements at different heights remains relatively stable over longer periods
   - This stability of long-term relationships enables us to use time-averaged profiles as reliable fallback parameters

These assumptions guide our two-tier reconstruction approach:
1. Primary: Use same-hour measurements when available (leveraging temporal stability)
2. Fallback: Use time-averaged profiles when hourly data is insufficient (leveraging profile continuity)

## Wind Direction Reconstruction

### Vector Averaging

Wind directions are circular quantities (0° and 360° are the same), so special handling is required for averaging:

1. Each direction is converted to vector components (x,y) using:
   ```julia
   x = speed * sin(direction)
   y = speed * cos(direction)
   ```

2. The x and y components are averaged separately
3. The averaged components are converted back to a direction using:
   ```julia
   direction = mod(atan(x, y) * 180/π + 360, 360)
   ```

### Direction Difference Calculation

When calculating differences between wind directions at different heights:

1. The shortest angular distance is used (e.g., difference between 350° and 10° is 20°, not 340°)
2. Direction differences are calculated using vector averaging over the period of interest

### Reconstruction Process

The direction reconstruction follows these steps:

1. For each missing measurement:
   - First attempts to use the nearest height with valid data at that timestamp
   - Calculates direction difference using vector averaging of available data
   - Applies this difference to reconstruct the missing value

2. Fallback Mechanism:
   - If direct reconstruction fails, uses a time-mean constant direction difference
   - Time-mean difference is calculated using all available valid data points between heights
   - First tries using the nearest lower height, then the nearest higher height if needed

## Wind Speed Reconstruction

Wind speed reconstruction uses the wind shear profile between different measurement heights.

### Wind Shear Profile

The wind shear profile is modeled using the power law:

```
V2 = V1 * (h2/h1)^α
```

Where:
- V1, V2 are wind speeds at heights h1, h2
- α is the shear exponent
- h1, h2 are the measurement heights

### Reconstruction Process

1. For each missing measurement:
   - Identifies valid measurements at other heights
   - Calculates shear exponent using available data
   - Applies shear profile to reconstruct missing value

## Implementation Details

### Data Structures

Key data structures used in reconstruction:

1. `DirectionCorrelation`:
   - `source_height`: Height of reference measurement
   - `target_height`: Height of reconstruction target
   - `mean_difference`: Average directional difference

2. `WindSpeedProfile`:
   - `reference_height`: Height of reference measurement
   - `shear_exponent`: Calculated shear exponent

### Results Tracking

Reconstruction results are tracked using:

1. `ReconstructedSuccess`:
   - `timestamp`: Time of reconstruction
   - `columnName`: Target sensor column
   - `value`: Reconstructed value

2. `ReconstructedFailure`:
   - `timestamp`: Time of reconstruction attempt
   - `columnName`: Target sensor column
   - `reason`: Explanation of failure

## Usage

The reconstruction process is typically run as part of the data processing pipeline:

```julia
using CleanMastProject.Command.ReconstructSingleMast

# Execute reconstruction for project directory
ReconstructSingleMast.execute("path/to/project")
```

### Output Files

The process generates several output files:

1. `reconstruct_single_mast.{original_file}.csv`: Processed data with reconstructed values
2. `reconstruct_single_mast-sensors.yaml`: Updated sensor configurations
3. `single-reconstruction.yaml`: Detailed reconstruction results

### Statistics

The process provides detailed statistics including:
- Total reconstruction attempts
- Success/failure counts
- Success rate percentage
- Per-sensor reconstruction counts

## Best Practices

1. Quality Control:
   - Verify sensor heights and configurations
   - Check reconstruction statistics for reasonableness
   - Review failure reasons for systematic issues

2. Validation:
   - Compare reconstructed values with historical patterns
   - Verify direction differences are physically reasonable
   - Check wind shear profiles against expected ranges

3. Limitations:
   - Direction reconstruction works best with small height differences
   - Wind shear profiles assume relatively uniform conditions
   - Time-mean differences assume stable directional patterns 