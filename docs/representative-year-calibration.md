# Representative Year Calibration

This document explains the process of representative year calibration in the CleanMast project, which adjusts wind measurements to account for long-term variations and create a representative dataset.

## Overview

The representative year calibration process adjusts wind measurements from a measurement campaign to better represent long-term conditions using mesoscale (MESO) data as a reference. The calibration is performed for a specific target height (defaults to 120.0m if not specified in configuration). The process involves:

1. Data Preparation
2. Finding Representative Year
3. Directional Calibration
4. Applying Calibration Factors

## Target Height Selection

- The calibration is performed for a single target height
- The target height can be specified in the configuration (`analysis.target_height`)
- If not specified, defaults to 120.0 meters
- The process finds the wind speed sensor closest to the target height for both mast and mesoscale data

## Detailed Process

### 1. Data Preparation

- Both mast and mesoscale data are averaged to hourly resolution
- Wind direction calculations use circular statistics to handle the 0-360° transition
- Data is filtered to the specified training time range

### 2. Finding Representative Year

The process identifies the most recent year in the mesoscale data that best represents the long-term conditions:

1. Calculates the full-period mean wind speed from mesoscale data
2. Compares each year's mean speed with the full-period mean
3. Selects the most recent year where the difference is within a threshold (default 2%)

### 3. Directional Calibration

The calibration is direction-sector specific, using 16 sectors (22.5° each):

1. For each direction sector:
   - Filters data for measurements within ±11.25° of sector center
   - Calculates sector-specific calibration using linear regression
   - Determines speed differences between training period and reference year

2. Calibration factors include:
   - Slope from linear regression between mast and meso data
   - Speed difference between training period and reference year means

### 4. Applying Calibration

The calibration is applied to the wind speed measurements:

1. For each measurement:
   - Determines the direction sector
   - Applies the sector-specific calibration factors
   - Validates results are within acceptable range (default 0.5-25.0 m/s)

## Implementation Details

### Key Functions

- `average_to_hourly`: Averages time series to hourly resolution
- `find_representative_year`: Identifies the most suitable reference year
- `calculate_directional_calibrations`: Computes direction-specific calibration factors
- `apply_calibration`: Applies the calibration to the dataset

### Validation and Safety Checks

- Minimum data requirements for each sector
- Valid wind speed range checks (0.5-25.0 m/s by default)
- Circular statistics for direction calculations
- Missing data handling

## Usage

The calibration is typically run after meso reconstruction:

1. Reads reconstructed mast data
2. Loads corresponding mesoscale data
3. Performs calibration
4. Saves calibrated data and sensor configuration

## Output Files

The process generates two files:
1. `rep_year_calibration.[original_filename].csv`: Calibrated time series data
2. `rep_year_calibration-sensors.yaml`: Sensor configuration file 