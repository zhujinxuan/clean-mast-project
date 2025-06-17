# Analyze Reconstruct-Single Command

The `analyze reconstruct-single` command compares time series data before and after single mast reconstruction, providing comprehensive analysis of reconstruction effectiveness.

## Usage

```bash
julia bin/CleanMast.jl analyze reconstruct-single path/to/analyze-reconstruct-single.yaml
```

## Configuration File Format

The YAML configuration file should have the following structure:

```yaml
masts:
  - name: String                    # Mast identifier
    before_reconstruction:
      csv: String                   # Path to CSV file before reconstruction
      sensorConfig: String          # Path to sensor configuration YAML
    after_reconstruction:
      csv: String                   # Path to CSV file after reconstruction
      sensorConfig: String          # Path to sensor configuration YAML
output:
  dir: String?                      # Output directory (default: ./analyze-reconstruct-single)
```

Paths can be either absolute or relative to the YAML configuration file location.

## Output

The command generates the following analyses for each mast:

### 1. Data Coverage Analysis
- **Missing data points** count before and after reconstruction
- **Reconstruction rate**: percentage of missing data that was successfully reconstructed
- **Data coverage ratio**: percentage of non-missing data after reconstruction
- Separate statistics for wind speed and wind direction channels

### 2. Wind Speed Correlation Analysis
- **R² matrix** showing correlations between all height pairs
- **Grid plots** with scatter plots and linear regression for:
  - Heights ≥ 100m vs Heights ≥ 100m
  - Heights ≥ 100m vs Heights < 100m
  - Heights < 100m vs Heights < 100m
- Each plot includes R² values and regression lines

### 3. Wind Direction Difference Analysis
- **Mean difference matrix**: average wind direction differences between height pairs
- **Standard deviation matrix**: variability of wind direction differences
- Circular statistics properly handle the 0°/360° wraparound

### 4. Comprehensive Report
A Typst report (`reconstruction_analysis_report.typ`) is generated in Chinese, containing:
- Executive summary
- Detailed tables for all analyses
- Embedded visualizations
- Statistical summaries

## Data Processing

### Time Series Regularization
- Both before and after datasets are regularized to 10-minute intervals
- Missing timestamps are filled with `missing` values
- Only the overlapping time range is analyzed

### Missing Data Handling
- Missing values are properly tracked and reported
- Reconstruction effectiveness is calculated based on missing data reduction
- Statistical calculations skip missing values appropriately

## Example

```yaml
# analyze-reconstruct-single.yaml
masts:
  - name: Mast01
    before_reconstruction:
      csv: ./timeseries/tower-shading/Mast01.csv
      sensorConfig: ./sensors/Mast01.yaml
    after_reconstruction:
      csv: ./timeseries/reconstruct-single/Mast01.csv
      sensorConfig: ./sensors/Mast01.yaml
  - name: Mast02
    before_reconstruction:
      csv: ./timeseries/tower-shading/Mast02.csv
      sensorConfig: ./sensors/Mast02.yaml
    after_reconstruction:
      csv: ./timeseries/reconstruct-single/Mast02.csv
      sensorConfig: ./sensors/Mast02.yaml
output:
  dir: ./reconstruction-analysis
```

This will analyze both Mast01 and Mast02, comparing their data before and after reconstruction, and save all results in the `./reconstruction-analysis` directory. 