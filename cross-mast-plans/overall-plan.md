# Cross-Mast Reconstruction System - Overall Plan

## 📋 Document Usage & Maintenance Guide

### Purpose
This document serves as the **complete architectural blueprint** for the cross-mast reconstruction feature. It captures all design decisions, model structures, workflows, and implementation phases.

### Document Lifecycle
- **During Development**: Living reference for implementation decisions
- **After Implementation**: Becomes a changelog/historical record of what was built

### How to Use This Document
1. **Before Implementation**: Review for complete understanding of architecture
2. **During Implementation**: Reference for design decisions and specifications
3. **Code Reviews**: Verify implementations match the plan
4. **Future Modifications**: Understand original design intent

### Maintenance Guidelines

#### What to Update
- ✅ Design refinements discovered during implementation
- ✅ Specification clarifications
- ✅ Additional architectural decisions
- ✅ Lessons learned that affect the design

#### What NOT to Change
- ❌ Original design decisions (mark as superseded instead)
- ❌ Remove content (strike through if obsolete)
- ❌ Implementation details (those go in current-plan.md)

#### Update Format
When updating, use clear markers:
```markdown
**Update 2024-12-20**: Changed model storage from individual files to...
**Superseded**: ~~Original design used individual sensor files~~
```

**Update 2024-12-20**: Changed overlap measurement from months to days for consistency:
- `overlap_months::Float64` → `overlap_days::Float64` in MastPairCoverage struct
- Selection criteria: ≥4 months → ≥120 days overlap requirement  
- More accurate since months vary in length (28-31 days) while days are consistent

**Update 2024-12-20**: Simplified DataCoverage return behavior:
- `analyze_mast_pair_coverage` now returns `Union{MastPairCoverage, Nothing}`
- Returns `nothing` when no wind speed sensors found or no valid timestamps
- Eliminates zero-value MastPairCoverage returns for cleaner error handling

### Transition to Changelog
After feature completion:
1. Add implementation summary at the top
2. Mark document as "IMPLEMENTED"
3. Add links to relevant PRs/commits
4. Archive as part of feature documentation

---

## System Overview

The cross-mast reconstruction system enables wind data reconstruction using measurements from nearby masts instead of mesoscale data sources. This system follows the established pattern: `(model, cross_mast_data) => reconstruct this mast data`.

### Three Main Commands

1. **recommend train-reconstruct-cross** - ✅ **IMPLEMENTED** - Generate configuration for training
2. **train reconstruct-cross** - ✅ **IMPLEMENTED** - Perform cross-mast analysis and model training
3. **recommend reconstruct-cross** - ✅ **IMPLEMENTED** - Generate configuration for reconstruction (commit 6e1607b)
4. **process reconstruct-cross** - ✅ **IMPLEMENTED** - Execute reconstruction using trained models (ready for commit)

**Future Command (Reserved)**: **analyze reconstruct-cross** - Generate/analyze results from trained models

## Core Architecture

### Model Design Philosophy

Following the existing meso reconstruction patterns but adapted for mast-to-mast relationships:

- **One model per mast-pair relationship** (not per sensor pair)
- **Separate speed and direction models** (following AbstractSpeedReferenceModel/AbstractDirectionReferenceModel)
- **Multiple sensor pairs within each model** (like SectorizedRegressionModel and DirectionOffsetModel)
- **Standard reconstruct function signature**: `reconstruct(model, source_timeseries) -> target_timeseries`

### Model Types

#### CrossMastSpeedModel
```julia
struct CrossMastSpeedPair
    target_sensor::SensorColumn
    source_sensor::SensorColumn
    slope::Float64
    intercept::Float64
    correlation::Float64
    r_squared::Float64
    rmse::Float64
end

struct CrossMastSpeedModel <: AbstractSpeedReferenceModel
    target_mast_name::String
    source_mast_name::String
    pairs::Vector{CrossMastSpeedPair}
end
```

#### CrossMastDirectionModel
```julia
struct CrossMastDirectionPair
    target_sensor::SensorColumn
    source_sensor::SensorColumn
    offset::Float64
    std_deviation::Float64
end

struct CrossMastDirectionModel <: AbstractDirectionReferenceModel
    target_mast_name::String
    source_mast_name::String
    pairs::Vector{CrossMastDirectionPair}
end
```

### Analysis Result Types

All analysis result types are defined in a single module `Types/CrossMastAnalysisResults.jl`:

#### MastPairCoverage
```julia
struct MastPairCoverage
    overlap_start::DateTime
    overlap_end::DateTime
    overlap_days::Float64
    concurrent_records::Int
    coverage_percentage::Float64
end
```

#### SpeedCorrelationResult
```julia
struct SpeedCorrelationResult
    target_sensor::SensorColumn
    source_sensor::SensorColumn
    correlation::Float64
    r_squared::Float64
    rmse::Float64
    slope::Float64
    intercept::Float64
    data_points::Int
end
```

#### DirectionAnalysisResult
```julia
struct DirectionAnalysisResult
    target_sensor::SensorColumn
    source_sensor::SensorColumn
    mean_offset::Float64
    std_deviation::Float64
    data_points::Int
end
```

#### MastPairAnalysisResult
```julia
struct MastPairAnalysisResult
    target_mast::String
    source_mast::String
    coverage::MastPairCoverage
    windspeed_correlations::Vector{SpeedCorrelationResult}
    winddirection_analysis::Vector{DirectionAnalysisResult}
    windspeed_model_file::Union{String, Nothing}
    winddirection_model_file::Union{String, Nothing}
end
```

### File Organization

```
./analyze-reconstruct-cross/
├── analyze-results.toml                    # Machine-readable results
├── report.html                            # Human-readable analysis report
├── cross-mast-models/                     # Trained model files
│   ├── Mast1/
│   │   ├── Mast2/
│   │   │   ├── windspeed.jld2             # ONE model for all speed sensor pairs
│   │   │   └── winddirection.jld2         # ONE model for all direction sensor pairs  
│   │   └── Mast3/
│   │       ├── windspeed.jld2
│   │       └── winddirection.jld2
│   └── Mast2/
│       └── Mast1/
│           ├── windspeed.jld2
│           └── winddirection.jld2
└── charts/                                # Analysis charts and plots
    ├── correlation_matrix.png
    ├── direction_differences.png
    └── coverage_timeline.png
```

## Selection Criteria

### High-Elevation Focus
- **Wind Speed**: Correlation ≥0.7 among sensors ≥120m height
- **Wind Direction**: Std deviation ≤12.5° among sensors ≥120m height
- **Data Coverage**: ≥120 days overlap requirement
- **Priority**: Rank by correlation strength (highest first)

### Model Selection Logic
```toml
# analyze-results.toml structure
[[mast_pairs]]
target_mast = "Mast1"
source_mast = "Mast2"
overlap_days = 258.5
overlap_start = "2023-01-01T00:00:00"
overlap_end = "2023-09-15T23:50:00"

windspeed_model_available = true
high_elevation_windspeed_correlation = 0.85    # Best correlation among sensors ≥120m
windspeed_model_file = "./cross-mast-models/Mast1/Mast2/windspeed.jld2"

winddirection_model_available = true
high_elevation_winddirection_std = 8.3         # Best std deviation among sensors ≥120m
winddirection_model_file = "./cross-mast-models/Mast1/Mast2/winddirection.jld2"
```

## Configuration Formats

### Train Configuration (Simple)
```toml
[[masts]]
name = "Mast1"
input.data = "./clean/Mast1.csv"
input.sensors = "./clean/Mast1.sensors.yaml"

[[masts]]
name = "Mast2" 
input.data = "./clean/Mast2.csv"
input.sensors = "./clean/Mast2.sensors.yaml"

[train]
output_dir = "./train-reconstruct-cross"
```

### Reconstruct Configuration (Generated)
```toml
[[masts]]
name = "TargetMast"
input.data = "./reconstruct-single/TargetMast.csv"
input.sensors = "./reconstruct-single/TargetMast.sensors.yaml"
output.data = "./reconstruct-cross/TargetMast.csv"
output.sensors = "./reconstruct-cross/TargetMast.sensors.yaml"

[[masts.models]]
cross_mast_name = "SourceMast1"
windspeed = "./cross-mast-models/TargetMast/SourceMast1/windspeed.jld2"
winddirection = "./cross-mast-models/TargetMast/SourceMast1/winddirection.jld2"

[[masts.models]]
cross_mast_name = "SourceMast2"  
windspeed = "./cross-mast-models/TargetMast/SourceMast2/windspeed.jld2"
# winddirection omitted - didn't meet std deviation criteria
```

## Complete Workflow

### 1. recommend train-reconstruct-cross ✅ **IMPLEMENTED**
- Input: Project directory with mast data
- Processing: Scan for mast time series files
- Output: Simple train config TOML listing all masts
- **Status**: Working CLI command available

### 2. train reconstruct-cross ✅ **IMPLEMENTED**
- Input: train config TOML
- Processing:
  - Load all mast time series data
  - Calculate correlations between all mast pairs
  - Calculate direction differences and standard deviations
  - Analyze data coverage overlaps
  - Train cross-mast models for all qualified pairs
  - Save models as JLD2 files
- Output:
  - train-results.toml (machine-readable statistics)
  - JLD2 model files in organized directory structure
- **Status**: Working CLI command available, full workflow implemented

### 3. recommend reconstruct-cross ❌ **NOT IMPLEMENTED**
- Input: train-results.toml
- Processing:
  - Apply selection criteria (≥120 days, ≥0.7 correlation, ≤12.5° std)
  - Rank by correlation strength
  - Generate config with paths to qualified models
- Output: reconstruct-cross.toml config
- **Status**: Needs implementation (see plan-reconstruct-cross.md)

### 4. process reconstruct-cross ❌ **NOT IMPLEMENTED**
- Input: reconstruct-cross.toml config
- Processing: Load models, apply reconstructions, merge data
- Output: Reconstructed mast time series
- **Status**: Needs implementation (see plan-reconstruct-cross.md)

### 5. analyze reconstruct-cross (future implementation - reserved)
- Input: train-results.toml or other analysis targets
- Processing: Generate analysis reports, visualizations, model comparisons
- Output: Analysis reports and insights
- **Status**: Future enhancement

## Implementation Structure

### Phase 1: Foundation (Types and Core Architecture) ✅ **COMPLETED**
**Scope**: All fundamental types and interfaces needed for the complete system
- Configuration types for all commands
- Model types (CrossMastSpeedModel, CrossMastDirectionModel)
- Analysis result types
- Follows existing project patterns for type organization
- **Status**: All types implemented and working

### Phase 2: Train Command System ✅ **COMPLETED**
**Scope**: Complete implementation of cross-mast analysis and model training
- **Details**: See `plan-train-reconstruct-cross.md` for comprehensive implementation plan
- **Key Output**: train-results.toml and trained JLD2 model files
- **Module**: TrainReconstructCross/
- **Status**: Fully implemented, CLI commands working, complete workflow operational

### Phase 3: Recommend Command System ✅ **IMPLEMENTED**
**Scope**: Intelligent model selection based on analysis results
- **Function**: Reads train-results.toml, applies selection criteria
- **Key Output**: reconstruct-cross.toml configuration
- **Selection Logic**: ≥120 days overlap, ≥0.7 correlation, ≤12.5° std deviation
- **Module**: ReconstructCross/ (implemented in commit 6e1607b)
- **Status**: Fully implemented with priority-based job generation

### Phase 4: Reconstruction Model Interface ✅ **COMPLETED**
**Scope**: Standard reconstruct functions for cross-mast models
- **Interface**: `reconstruct(model, source_timeseries) -> target_timeseries`
- **Implementation**: Already implemented in CrossMastSpeedCorrelation.jl and CrossMastDirectionAnalysis.jl
- **Purpose**: Enables actual data reconstruction using trained models
- **Status**: Working reconstruct functions available

### Phase 5: Process Command System ✅ **IMPLEMENTED**
**Scope**: Complete reconstruction workflow using trained models
- **Function**: Loads models, applies reconstructions, merges results
- **Input**: reconstruct-cross.toml and JLD2 model files
- **Key Output**: Reconstructed mast time series
- **Module**: ReconstructCross/ (ProcessReconstructCrossCommand.jl implemented)
- **Status**: Fully implemented with quality metrics and campaign summary

### Integration Strategy
- **CLI Registration**: All commands registered in CleanMastCli.jl
- **Module Structure**: Each major component as separate module in CleanMastProject.jl
- **Data Flow**: train → recommend → process (following existing meso pattern)
- **Compatibility**: Seamless integration with existing reconstruction workflow

## Key Design Decisions

1. **Efficiency**: One model file per mast-pair per variable type (not per sensor pair)
2. **Standards Compliance**: Follows existing AbstractMastReferenceModel interface
3. **High-Quality Focus**: Selection based on ≥120m sensors for wind energy relevance
4. **Data-Driven**: Intelligent selection based on statistical criteria
5. **Extensible**: Modular design allows easy addition of new analysis types
6. **Robust**: Handles missing data and edge cases appropriately
7. **Integration**: Seamlessly fits with existing meso reconstruction workflow
8. **Type Organization**: Related simple types (like analysis results) grouped in single modules following existing patterns (e.g., AnalyzeReconstructSingleConfiguration.jl)

This architecture provides a comprehensive, efficient, and maintainable cross-mast reconstruction system that leverages the existing codebase patterns while addressing the specific requirements of mast-to-mast relationships.