# Representative Year Report Generation Plan

## Overview

This plan outlines the implementation of a comprehensive report generation system for representative year calibration analysis in the CleanMastProject. The reports will provide detailed analysis of climatology selection, representative year calibration, and sector-wise performance metrics.

## 1. Report Module Structure

### Primary Module: `src/RepresentativeYear/ReportGeneration.jl`
- Generate comprehensive Typst reports for representative year calibration analysis
- Include bilingual (Chinese/English) support following existing patterns
- Follow the sensor naming conventions established in `docs/sensor-naming-conventions.md`
- Use `create_sensor_short_name()` function for consistent sensor identification

## 2. Report Content Structure

### Executive Summary Section
- Overview of representative year selection process across all mast-meso pairs
- Summary statistics showing calibration effectiveness
- Overall calibration status distribution (applied/not needed)
- Performance metrics summary

### For Each Mast-Meso Pair Analysis

#### Climatology & Representative Year Analysis
- **Full period meso mean wind speed** (climatology baseline)
- **Training period meso mean wind speed** (actual measurement period) 
- **Representative year meso mean wind speed** (if calibration applied)
- **Selected representative year start date** (if calibration applied)
- **Calibration threshold status** and reasoning for selection
- **Percentage deviation** from climatology

#### 16-Sector Detailed Analysis Tables

**Table Structure:**
```
| Sector | Training Period | Representative Year | Speed Difference | Slope | Intercept | Data Points |
|--------|----------------|--------------------|--------------------|-------|-----------|-------------|
| N      | 8.5 m/s        | 8.3 m/s           | -0.2 m/s          | 1.05  | 0.12      | 1,234       |
| NNE    | 8.7 m/s        | 8.6 m/s           | -0.1 m/s          | 1.02  | 0.08      | 1,156       |
| ...    | ...            | ...                | ...               | ...   | ...       | ...         |
```

**Data Elements per Sector:**
- Sector names (N, NNE, NE, ENE, E, ESE, SE, SSE, S, SSW, SW, WSW, W, WNW, NW, NNW)
- Training period sectoral meso wind speeds
- Representative year sectoral meso wind speeds (if calibration applied)
- Meso speed differences (representative_year_mean - training_period_mean)
- Slope coefficients per sector (from linear regression)
- Intercept values per sector (from linear regression)
- Data point counts per sector for quality assessment

#### Sensor-Level Calibration Analysis (Filtered)

**Selection Criteria:**
- Wind speed sensors ≥100m height (if available)
- OR highest wind speed sensor (if no sensors ≥100m)

**Information per Selected Sensor:**
- Sensor names using standardized convention: `{sensorStyleShortName}:{height}m:{sensorDirection}` or `{sensorStyleShortName}:{height}m` (if direction is N/A)
- Corresponding meso direction sensor used (highest available sensor)
- Calibration applied status per sensor (Yes/No)
- Number of directional calibrations applied (should be 16 for complete coverage)

#### Grid Visualizations and Heatmaps

**16-Sector Performance Grid:**
- Heatmap showing slope values across all 16 sectors
- Heatmap showing intercept values across all 16 sectors
- Color-coded visualization of sector performance
- Visual comparison tables for training vs representative year patterns

### Conditional Display Logic

**If Representative Year Calibration Applied:**
- Show complete analysis with slopes, intercepts, representative year data
- Include 3-way comparison: Climatology vs Training vs Representative Year
- Display calibration effectiveness metrics

**If No Calibration Needed:**
- Show simplified analysis with climatology vs training comparison only
- Explain why calibration wasn't needed (within threshold criteria)
- Focus on data quality and representativeness metrics

## 3. Implementation Components

### New Files to Create

#### `src/RepresentativeYear/ReportGeneration.jl`
**Primary Functions:**
- `generate_representative_year_report(analysis_results, config, output_dir)` - Main report generator
- `extract_calibration_analysis_data(calibration_results)` - Data extraction from CalibrationResults
- `create_climatology_summary_table(meso_data, analysis_periods)` - Overall statistics
- `create_sector_comparison_tables(sector_data)` - 16-sector analysis tables
- `create_sensor_analysis_table(sensors, calibration_info)` - Filtered sensor analysis
- `format_sensor_names_for_report(sensors)` - Apply naming conventions
- `generate_sector_heatmaps(sector_data, output_dir)` - Visualization generation

#### `src/RepresentativeYear/ReportRepresentativeYearCommand.jl`
**CLI Command Functions:**
- `execute(config_path_or_project_dir)` - Main command entry point
- `load_calibration_results(project_dir)` - Load existing calibration data
- `analyze_representative_year_performance(results)` - Performance analysis
- `generate_report_data_structure(analysis)` - Prepare data for reporting

#### Integration Points
- Add command to `src/CleanMastCli.jl` as `"report representative-year"`
- Follow existing CLI patterns for consistency

### Data Flow Architecture

1. **Input Loading:**
   - Load calibration results from `process-stats/representative-year-info-<mast>.yaml`
   - Load original configuration from `representative-year.toml`
   - Load meso data for climatology analysis

2. **Data Analysis:**
   - Extract 16-sector statistics from CalibrationResults structures
   - Calculate climatology vs training vs representative year comparisons
   - Analyze sensor-level calibration effectiveness
   - Compute performance metrics and quality indicators

3. **Report Generation:**
   - Generate comprehensive Typst report with embedded tables and plots
   - Create supporting CSV data files for further analysis
   - Generate visualization plots and heatmaps
   - Export summary statistics

4. **Output Structure:**
   ```
   project-dir/
   ├── representative-year-report/
   │   ├── report.typ                          # Main Typst report
   │   ├── tables/
   │   │   ├── climatology_summary.typ
   │   │   ├── sector_analysis_<mast>.typ
   │   │   └── sensor_calibration_<mast>.typ
   │   ├── plots/
   │   │   ├── sector_heatmaps_<mast>.png
   │   │   └── calibration_overview.png
   │   └── data/
   │       ├── sector_analysis.csv
   │       ├── calibration_summary.csv
   │       └── sensor_performance.csv
   ```

## 4. Technical Implementation Details

### Data Structures Required

#### Analysis Results Structure
```julia
struct RepresentativeYearAnalysis
    mast_name::String
    meso_name::String
    climatology_mean::Float64
    training_mean::Float64
    representative_year_mean::Union{Float64, Nothing}
    representative_year_start::Union{DateTime, Nothing}
    calibration_applied::Bool
    sector_analysis::DataFrame  # 16-sector detailed data
    sensor_analysis::Vector{SensorCalibrationInfo}
    performance_metrics::Dict{String, Float64}
end
```

#### Sector Analysis DataFrame Structure
```julia
# Columns: sector, training_mean, representative_mean, speed_diff, slope, intercept, data_points
```

### Integration with Existing Systems

#### Sensor Naming Integration
- Use `CleanMastProject.Types.SensorColumns.create_sensor_short_name()` for all sensor references
- Ensure consistency with `docs/sensor-naming-conventions.md`
- Apply standardized naming in all report outputs

#### Report Generation Patterns
- Follow existing Typst report patterns from `src/AnalyzeReconstructSingle/ReportGeneration.jl`
- Use bilingual (Chinese/English) text constants
- Maintain consistent formatting and styling

#### CLI Integration
- Follow existing command patterns in CleanMastCli.jl
- Support both config file and project directory input modes
- Provide helpful error messages and progress indicators

## 5. Quality Assurance and Testing

### Test Coverage Required
- Unit tests for data extraction functions
- Integration tests for report generation
- Validation tests for Typst output format
- CLI command testing

### Validation Criteria
- Accurate data extraction from CalibrationResults
- Correct 16-sector analysis calculations
- Proper sensor filtering (≥100m or highest)
- Consistent naming convention application
- Valid Typst report generation

## 6. Future Enhancements

### Potential Extensions
- Interactive web-based report generation
- Additional visualization options (3D plots, animated comparisons)
- Export to other formats (PDF, HTML, Excel)
- Integration with external reporting tools
- Automated report scheduling and distribution

### Performance Optimizations
- Parallel processing for multiple mast analysis
- Caching of intermediate calculations
- Optimized data structures for large datasets
- Memory-efficient plot generation

This comprehensive plan provides the foundation for implementing a robust representative year report generation system that integrates seamlessly with the existing CleanMastProject infrastructure while providing valuable insights into calibration effectiveness and data quality.