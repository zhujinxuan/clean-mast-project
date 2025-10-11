# 2025-10-11: Meso-Mast Reconstruction Quality Report

## Overview
Implemented a comprehensive reporting system for analyzing meso-mast reconstruction quality, providing RMSE and correlation metrics between mesoscale data and mast measurements.

## Changes Made

### 1. New Report Module
- **Module**: `ReportReconstructMeso` with full analysis, visualization, and reporting capabilities
- **Purpose**: Evaluate which meso data sources are used for each mast and their reconstruction quality
- **Output**: Chinese Typst reports with scatter plots and quality metrics

### 2. Core Components Implemented

#### Configuration Type
- `src/Types/ReportReconstructMesoConfig.jl`: Configuration structure for report generation

#### Analysis Pipeline
- `src/ReportReconstructMeso/AnalysisCore.jl`: Data loading and metrics calculation (RMSE, correlation)
- `src/ReportReconstructMeso/DataVisualization.jl`: Scatter plots using AlgebraOfGraphics
- `src/ReportReconstructMeso/ReportGeneration.jl`: Chinese Typst report generation with tables and plots

#### Commands
- `src/ReportReconstructMeso/CommandReportReconstructMeso.jl`: Main report execution
- `src/ReportReconstructMeso/RecommendReportReconstructMesoCommand.jl`: Config file generation

### 3. CLI Commands Added

```bash
# Generate report configuration
julia bin/CleanMast.jl recommend report-reconstruct-meso <project-dir>

# Generate reconstruction quality report
julia bin/CleanMast.jl report reconstruct-meso <config-path>
```

### 4. Integration with Batch Workflows

#### Report All Command
- Added as "Report 7/7: Reconstruct Meso Report"
- Automatically generates meso-mast reconstruction quality report

#### Recommend Report All Command
- Added as "Config 6/6: Reconstruct Meso Report Configuration"
- Generates config from existing `reconstruct-meso.toml`

### 5. Report Features

#### Metrics Analyzed
- **RMSE**: Root Mean Square Error between meso and mast wind speeds
- **Correlation**: Pearson correlation coefficient for wind speed sensors
- **Sensor Focus**: Top 3 highest wind speed sensors (statType = avg)

#### Visualizations
- Scatter plots for each mast-meso pair
- Regression lines showing reconstruction fit
- Side-by-side sensor comparisons

#### Output Structure
```
report-masts/reconstruct-meso/
├── report.typ                          # Main Chinese Typst report
├── tables/
│   └── {mast}_{meso}_summary.typ      # Summary tables
├── plots/
│   └── {mast}_{meso}_sensors.png      # Scatter plots
└── data/
    └── {mast}_{meso}_metrics.csv      # CSV exports
```

## Technical Implementation

### Files Created
- `src/Types/ReportReconstructMesoConfig.jl`
- `src/ReportReconstructMeso.jl` (module aggregator)
- `src/ReportReconstructMeso/AnalysisCore.jl`
- `src/ReportReconstructMeso/DataVisualization.jl`
- `src/ReportReconstructMeso/ReportGeneration.jl`
- `src/ReportReconstructMeso/CommandReportReconstructMeso.jl`
- `src/ReportReconstructMeso/RecommendReportReconstructMesoCommand.jl`

### Files Modified
- `src/CleanMastProject.jl`: Added module export
- `src/CleanMastCli.jl`: Added CLI commands
- `src/ReportAllMasts/ReportAllMastsCommand.jl`: Integrated as Report 7/7
- `src/ReportAllMasts/RecommendReportAllCommand.jl`: Integrated as Config 6/6

## Impact
- **Transparency**: Users can now see which meso data is used for each mast
- **Quality Assessment**: RMSE and correlation provide quantitative reconstruction quality metrics
- **Decision Support**: Helps validate meso data source selection and model performance
- **Workflow Integration**: Seamlessly integrated into batch reporting commands

## Design Patterns
- Follows established `AnalyzeReconstructCross` architecture pattern
- Uses functional programming style (map/filter, no imperative loops)
- Leverages AlgebraOfGraphics for declarative visualizations
- Maintains Chinese language consistency with other reports
