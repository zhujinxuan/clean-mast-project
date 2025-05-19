# Turbulence Intensity Analysis

This document describes how turbulence intensity (TI) is calculated and processed in the CleanMast project.

## Overview

Turbulence intensity analysis is performed using both wind speed average and standard deviation measurements at a target height. The process includes calculating time series TI values, sector statistics, and creating a Meteodyn-compatible TI matrix.

## Process Flow

1. **Sensor Selection**
   - Finds nearest wind speed average sensor at target height
   - Finds standard deviation sensor at the same height
   - Finds nearest wind direction sensor at target height

2. **Time Series Calculation**
   - TI is calculated as: `TI = wind_speed_std / max(wind_speed_avg, 1.0)`
   - A minimum wind speed threshold of 1.0 m/s is enforced
   - Each measurement is assigned to a direction sector

3. **Sector Statistics**
   - For each sector, calculates:
     - Mean wind speed
     - Mean TI
     - Standard deviation of TI
     - Number of occurrences
   - Overall statistics include:
     - Mean TI across all sectors
     - Standard deviation of TI
     - Representative TI (mean + standard deviation)

4. **Meteodyn Matrix**
   - Creates a matrix of TI values by wind speed bin and direction sector
   - Default wind speed bins: 0-28 m/s in 1 m/s increments
   - Requires minimum 5 samples per bin for reliable statistics
   - Uses mean TI for bins with insufficient data

## Output Files

The analysis produces four output files:

1. `turbulence_intensity.csv`
   - Contains sector-wise statistics
   - Columns: sector, mean speed, TI, standard deviation, occurrence

2. `turbulence_intensity_by_wind_speed.csv`
   - Contains TI statistics for each wind speed bin (1 m/s increments)
   - Columns: wind_speed_min, wind_speed_max, mean_ti, std_ti, occurrence, representative_ti
   - Useful for analyzing how TI varies with wind speed

3. `turbulence_intensity_report.csv`
   - Summary statistics
   - Contains: mast name, wind speed range, mean TI, representative TI, TI standard deviation
   - Includes statistics for different wind speed ranges:
     - All wind speeds
     - Wind speeds > 3 m/s
     - Wind speeds between 14.5 and 16.5 m/s
     - Wind speeds between 9.5 and 10.5 m/s

4. `meteodyn_ti.txt`
   - Formatted for Meteodyn WT input
   - Matrix of TI values by wind speed and direction sector

## Configuration

The target height for TI analysis is determined in the following order:
1. `analysis.ti_target_height` from config
2. `analysis.target_height` from config
3. Default value of 120.0m

## Prerequisites

Before running turbulence intensity analysis:
1. Tower shading correction must be completed
2. Required sensors must be configured in `tower-shading-sensors.yaml`
3. Project configuration must be valid

## Usage

To run the turbulence intensity analysis:

```bash
cleanmast analyze turbulence <project_directory>
``` 