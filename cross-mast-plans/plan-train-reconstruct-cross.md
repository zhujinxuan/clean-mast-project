# Cross-Mast Reconstruction - Train Command Implementation Plan

## 📋 Document Usage & Maintenance Guide

### Purpose
This document tracks the **active implementation progress** of the `train reconstruct-cross` command specifically. It serves as a working document for what's being built, what's completed, and what's next.

### Context
This is a detailed implementation plan for ONE command in the larger cross-mast reconstruction system. For the complete system architecture and overview of all commands, see `overall-plan.md`.

### Document Lifecycle
- **During Development**: Updated frequently as work progresses
- **After Implementation**: Becomes a detailed changelog of implementation steps

### How to Use This Document

#### For Implementers
1. **Before Starting**: Review current phase and implementation details
2. **During Work**: Update progress markers and notes
3. **After Completing**: Mark sections as completed with dates
4. **Blockers/Issues**: Document any deviations from plan

#### Progress Tracking Format
```markdown
### Phase 1: Core Data Structures ✅ Completed 2024-12-20
- [x] Types/TrainReconstructCrossConfig.jl - ✅ 2024-12-19
- [x] Types/CrossMastSpeedModel.jl - ✅ 2024-12-20
- [ ] Types/CrossMastDirectionModel.jl - 🚧 In Progress
```

### Maintenance Guidelines

#### Daily/Weekly Updates
- ✅ Mark completed items with dates
- ✅ Add implementation notes and discoveries
- ✅ Document any deviations from original plan
- ✅ Update "Next Steps" section

#### What to Track
- Implementation status (Not Started / In Progress / Completed)
- Completion dates
- Code review status
- Test coverage
- Integration status
- Blockers or issues encountered

#### Implementation Notes Format
```markdown
**Implementation Note 2024-12-20**: Discovered that CrossMastSpeedModel needs 
additional field for quality metrics. Added `quality_score::Float64`.
```

### Next Steps Section
Always maintain a "Next Steps" section at the bottom:
```markdown
## Next Steps (Updated: 2024-12-20)

**Phase 1 Status**: ✅ **COMPLETED** - All core data structures implemented with proper naming conventions, @with_kw decorators, and from_dict/to_dict methods

**Phase 2 Status**: ✅ **COMPLETED** - All analysis components implemented with major refactoring improvements:
- DataCoverage.jl: ✅ Overlap analysis between masts
- CrossMastSpeedCorrelation.jl: ✅ Wind speed correlation analysis with train/reconstruct functions
- CrossMastDirectionAnalysis.jl: ✅ Wind direction analysis with train/reconstruct functions
- CrossMastSummary.jl: ✅ Summary statistics and high-elevation filtering (separated for cleaner architecture)
- CrossMastTrainParams.jl: ✅ Parameter types for configurable training

**Major Refactoring Completed**: ✅ Struct consolidation, summary optimization, and module separation
- Eliminated redundant analysis result structs (SpeedCorrelationResult, DirectionAnalysisResult)
- Enhanced model component structs with data_points field
- Separated summary functions into dedicated module
- Simplified train() functions by removing conversion steps
- Optimized summary structs: removed redundant average fields, focused on actionable metrics
- Designed CrossMastReporting as separate module for reusable visualization and reporting

**Next Phase**: Phase 3 - Results Management and Reporting (serialization + CrossMastReporting module), then Phase 4 - Command Implementation

## Current Implementation Status

### ✅ Completed Files
```
src/Types/
├── TrainReconstructCrossConfig.jl ✅ (with @with_kw)
├── CrossMastSpeedModels.jl ✅ (enhanced with data_points field) 
├── CrossMastDirectionModels.jl ✅ (enhanced with data_points field)
├── CrossMastAnalysisResults.jl ✅ (optimized summary structs, unified types)
└── CrossMastTrainParams.jl ✅ (with @with_kw)

src/TrainReconstructCross/
├── DataCoverage.jl ✅ (complete with error handling)
├── CrossMastSpeedCorrelation.jl ✅ (complete with train/reconstruct functions)
├── CrossMastDirectionAnalysis.jl ✅ (complete with train/reconstruct functions)
└── CrossMastSummary.jl ✅ (optimized summary functions, actionable metrics only)
```

### 🚧 Planned Files (Phase 3)
```
src/TrainReconstructCross/
└── TrainReconstructCrossCommand.jl ⏳ (main command with inline TOML + model saving)

src/CrossMastReporting/ (New separate module)
├── ReportGeneration.jl ⏳ (AlgebraOfGraphics + CairoMakie visualization)
└── TypstTemplates.jl ⏳ (template management and content generation)
```

### 🔧 Ready to Test
All implemented components can now be tested with @with_kw keyword constructors:
```julia
# Example using keyword constructors
pair = CrossMastSpeedPair(
    target_sensor = target_sensor,
    source_sensor = source_sensor,
    slope = 0.85,
    intercept = 0.12,
    correlation = 0.75,
    r_squared = 0.56,
    rmse = 2.3
)
```

### Transition to Changelog

After feature completion:
1. Add summary of implementation timeline
2. List all completed components with dates
3. Document any deviations from original plan
4. Include performance metrics or test results
5. Link to PRs and commits
6. Create "Lessons Learned" section

---

## Focus: Train Reconstruct Cross Command

This document outlines the detailed implementation plan for the `train reconstruct-cross` command, which is the core analysis engine of the cross-mast reconstruction system.

## Command Overview

**Input**: `train-reconstruct-cross.toml` configuration file
**Output**: Complete analysis results including trained models and reports
**Purpose**: Analyze all mast-to-mast relationships and train cross-mast reconstruction models

## Input Configuration Format

```toml
# train-reconstruct-cross.toml
[[masts]]
name = "Mast1"
input.data = "./clean/Mast1.csv"
input.sensors = "./clean/Mast1.sensors.yaml"

[[masts]]
name = "Mast2" 
input.data = "./clean/Mast2.csv"
input.sensors = "./clean/Mast2.sensors.yaml"

[[masts]]
name = "Mast3"
input.data = "./clean/Mast3.csv"
input.sensors = "./clean/Mast3.sensors.yaml"

[train]
output_dir = "./train-reconstruct-cross"
```

## Implementation Phases

### Phase 1: Core Data Structures ✅ Completed 2024-12-20
**Location: Types/ directory** (All structs must be centralized in Types/)

**Implementation Note 2024-12-20**: Updated filenames to follow project conventions:
- Configuration files use `***Config.jl` pattern
- Model files use `***Models.jl` pattern
- Fixed module/struct naming conflicts by using different module names

**Implementation Note 2024-12-20 - Phase 2 Completed**: Successfully implemented all analysis components:
- Added Parameters.jl @with_kw decorators to all cross-mast types for keyword constructors
- DataCoverage.jl: Time series overlap analysis with concurrent data counting
- CrossMastSpeedCorrelation.jl: Wind speed correlation analysis with linear regression
- CrossMastDirectionAnalysis.jl: Wind direction difference analysis with circular math
- ModelTraining.jl: Model creation using @with_kw constructors and JLD2 serialization
- All components follow existing codebase patterns and include comprehensive error handling

**Implementation Note - DataCoverage Return Type**: `analyze_mast_pair_coverage` now returns `Union{MastPairCoverage, Nothing}` to handle cases where analysis is impossible:
- Returns `nothing` when no wind speed sensors found in either mast
- Returns `nothing` when no timestamp overlap exists between masts
- Returns `MastPairCoverage` with zero values when sensors exist but no valid data
- Main command loop filters out `nothing` results to only process valid analyses

**Implementation Note - Days vs Months**: Changed overlap measurement from months to days for consistency:
- `overlap_months::Float64` → `overlap_days::Float64` in MastPairCoverage struct
- Calculation: `(concurrent_records * 10.0) / (60.0 * 24.0)` for precise day conversion
- Selection criteria updated: ≥4 months → ≥120 days, minimum training threshold: 1 month → 30 days
- More accurate since months vary in length (28-31 days) while days are consistent

**Implementation Note - File Renaming**: Renamed `CrossMastCorrelation.jl` to `CrossMastSpeedCorrelation.jl` for semantic clarity:
- More specific naming distinguishes speed correlation from other types of correlation analysis
- Maintains consistency with `CrossMastDirectionAnalysis.jl` specific naming pattern
- Module name updated from `CrossMastCorrelation` to `CrossMastSpeedCorrelation`
- Future-proofs naming convention for additional correlation types (temperature, pressure, etc.)

**Implementation Note - Module Integration**: TrainReconstructCross module properly integrated into CleanMastProject.jl:
- Module entry point established in main project file following existing patterns
- All implemented analysis components (DataCoverage, CrossMastSpeedCorrelation, CrossMastDirectionAnalysis) are properly exported
- Module structure ready for Phase 3 components (ResultsSerialization, ReportGeneration) and Phase 4 commands

**Implementation Note - Architecture Simplification**: Eliminated ModelTraining.jl redundancy:
- train() and reconstruct() functions moved directly into analysis files following existing patterns
- CrossMastSpeedCorrelation.jl now includes train/reconstruct for CrossMastSpeedModel
- CrossMastDirectionAnalysis.jl now includes train/reconstruct for CrossMastDirectionModel
- Added parameter structs (CrossMastSpeedTrainParams, CrossMastDirectionTrainParams) for type-safe filtering
- Follows same pattern as SectorizedRegressionTraining.jl and SectorizedRegressionReconstruction.jl

**Implementation Note - Major Refactoring: Struct Consolidation**: Eliminated redundant analysis result structs:
- Enhanced CrossMastSpeedPair with data_points::Int field (was missing compared to SpeedCorrelationResult)
- Enhanced CrossMastDirectionPair with data_points::Int field (was missing compared to DirectionAnalysisResult)
- Removed SpeedCorrelationResult and DirectionAnalysisResult entirely (redundant with model structs)
- Updated MastPairAnalysisResult to use unified CrossMastSpeedPair and CrossMastDirectionPair types
- Updated all function signatures, return types, and imports across the codebase
- Simplified train() functions by eliminating conversion step between result and model types
- Preserved valuable data_points information while eliminating redundancy (4 structs → 2 structs)

**Implementation Note - Summary Module Separation**: Created dedicated summary module for cleaner architecture:
- CrossMastSummary.jl module contains summarize_correlations() and summarize_direction_analysis()
- Moved get_best_high_elevation_correlation() and get_best_high_elevation_direction_std() to summary module
- Centralized high-elevation filtering logic in summary functions
- Clean separation of analysis algorithms vs statistical summary operations
- Analysis modules (CrossMastSpeedCorrelation.jl, CrossMastDirectionAnalysis.jl) focused on core analysis only

**Implementation Note - Summary Struct Optimization**: Removed redundant average fields for cleaner diagnostics:
- CorrelationSummary: Removed `average_correlation` (includes irrelevant low-elevation sensors), kept `average_high_elevation_correlation` (wind energy focused)
- DirectionSummary: Removed `average_std_deviation`, `average_high_elevation_std`, `average_mean_offset` (not useful for direction diagnostics)
- Focus on actionable metrics: best correlations/std deviations for model selection, high-elevation averages for quality assessment
- Simplified summary functions to compute only essential statistics for cross-mast reconstruction decisions

**Implementation Note - Field Simplification**: Removed redundant r_squared and rmse fields for cleaner architecture:
- CrossMastSpeedPair: Removed `r_squared` field (mathematically redundant: r² = correlation²)
- CrossMastSpeedPair: Removed `rmse` field (correlation is sufficient for wind energy model selection)
- CrossMastSpeedTrainParams: Removed `min_r_squared` and `max_rmse` filtering parameters
- Analysis functions: Simplified to only calculate essential metrics (correlation, slope, intercept)
- Focus on correlation as the primary metric for cross-mast wind speed model quality assessment
- Reduced computational overhead and struct complexity while maintaining all necessary information

**Implementation Note - Serialization Simplification**: Discovered existing to_dict infrastructure eliminates need for separate ResultsSerialization module:
- CrossMastAnalysisResults.jl already contains complete to_dict implementations for all analysis types
- TOML generation becomes trivial: `[to_dict(result) for result in results]`
- ResultsSerialization.jl eliminated in favor of inline function in TrainReconstructCrossCommand.jl
- Simpler project structure with fewer files and cross-module dependencies
- Focus shifted to model saving functions as the main Phase 3 implementation need

**Usage Pattern Examples**:
```julia
# Analyze command (permissive filtering)
speed_params = CrossMastSpeedTrainParams(target_name="Mast1", source_name="Mast2")
# Strict filtering for recommend command
strict_params = CrossMastSpeedTrainParams(target_name="Mast1", source_name="Mast2", min_correlation=0.7)
speed_model = train(CrossMastSpeedModel, speed_params, target_ts, source_ts)

# Direct usage of unified structs
correlations = analyze_windspeed_correlations(target_ts, source_ts)  # Returns Vector{CrossMastSpeedPair}
summary = summarize_correlations(correlations)                        # Returns CorrelationSummary
best_correlation = get_best_high_elevation_correlation(correlations)  # Direct from analysis results

# Reconstruction
reconstructed_data = reconstruct(speed_model, source_ts)
```

#### File: `Types/TrainReconstructCrossConfig.jl`
```julia
struct TrainReconstructCrossConfiguration
    masts::Vector{TrainCrossMast}
    train::TrainCrossSettings
end

struct TrainCrossMast
    name::String
    input::TimeSeriesSource
end

struct TrainCrossSettings
    output_dir::String
end
```

#### File: `Types/CrossMastSpeedModels.jl`
```julia
struct CrossMastSpeedPair
    target_sensor::SensorColumn
    source_sensor::SensorColumn
    correlation::Float64
    slope::Float64
    intercept::Float64
    data_points::Int
end

struct CrossMastSpeedModel <: AbstractSpeedReferenceModel
    target_mast_name::String
    source_mast_name::String
    pairs::Vector{CrossMastSpeedPair}
end
```

#### File: `Types/CrossMastDirectionModels.jl`
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

#### File: `Types/CrossMastAnalysisResults.jl`
**Analysis Result Types** - Define analysis result structs in a single file for better organization:

```julia
module CrossMastAnalysisResults

using Dates
using ..SensorColumns: SensorColumn
using ..CrossMastSpeedModels: CrossMastSpeedPair
using ..CrossMastDirectionModels: CrossMastDirectionPair

export MastPairCoverage, CorrelationSummary, DirectionSummary, MastPairAnalysisResult

"""
    MastPairCoverage

Results from analyzing time series overlap between two masts.
"""
struct MastPairCoverage
    overlap_start::DateTime
    overlap_end::DateTime
    overlap_days::Float64
    concurrent_records::Int
    coverage_percentage::Float64
end

"""
    CorrelationSummary

Summary statistics from wind speed correlation analysis between two masts.
Focus on wind energy relevant metrics (≥120m sensors) and actionable diagnostics.
"""
struct CorrelationSummary
    total_pairs::Int
    high_elevation_pairs::Int
    best_correlation::Float64
    best_high_elevation_correlation::Float64
    average_high_elevation_correlation::Float64  # Wind energy focused metric
end

"""
    DirectionSummary

Summary statistics from wind direction analysis between two masts.
Focus on essential metrics for model selection and quality assessment.
"""
struct DirectionSummary
    total_pairs::Int
    high_elevation_pairs::Int
    best_std_deviation::Float64
    best_high_elevation_std::Float64  # Key metric for direction model selection
end

"""
    MastPairAnalysisResult

Complete analysis results for a single mast pair, including all correlations,
direction analyses, summary statistics, and trained model file paths.

Note: Uses unified CrossMastSpeedPair and CrossMastDirectionPair types that serve
both as analysis results and model components (after struct consolidation refactoring).
"""
struct MastPairAnalysisResult
    target_mast::String
    source_mast::String
    coverage::MastPairCoverage
    windspeed_correlations::Vector{CrossMastSpeedPair}      # Unified: was SpeedCorrelationResult
    winddirection_analysis::Vector{CrossMastDirectionPair}  # Unified: was DirectionAnalysisResult
    windspeed_summary::CorrelationSummary
    winddirection_summary::DirectionSummary
    windspeed_model_file::Union{String, Nothing}
    winddirection_model_file::Union{String, Nothing}
end

end # module
```

#### File: `Types/CrossMastTrainParams.jl`
**Training Parameter Types** - Define parameter structs for type-safe model training:

```julia
module CrossMastTrainParams

using Parameters

export CrossMastSpeedTrainParams, CrossMastDirectionTrainParams

"""
    CrossMastSpeedTrainParams

Parameters for training CrossMastSpeedModel with configurable filtering criteria.

# Fields
- `target_name::String`: Name of target mast (required, no default)
- `source_name::String`: Name of source mast (required, no default)
- `min_data_points::Int`: Minimum concurrent data points required (default: 100)
- `min_correlation::Float64`: Minimum correlation threshold (default: 0.0, recommend: 0.7)
- `min_r_squared::Float64`: Minimum R² threshold (default: 0.0, recommend: 0.5)
- `max_rmse::Float64`: Maximum RMSE threshold (default: Inf)
- `exclude_nan_results::Bool`: Filter out NaN/Inf values (default: true)
"""
@with_kw struct CrossMastSpeedTrainParams
    # Required names (no defaults)
    target_name::String
    source_name::String
    
    # Data quality filters (with defaults)
    min_data_points::Int = 100
    min_correlation::Float64 = 0.0           # recommend: 0.7
    min_r_squared::Float64 = 0.0             # recommend: 0.5
    max_rmse::Float64 = Inf                  # recommend: reasonable threshold
    exclude_nan_results::Bool = true
end

"""
    CrossMastDirectionTrainParams

Parameters for training CrossMastDirectionModel with configurable filtering criteria.

# Fields
- `target_name::String`: Name of target mast (required, no default)
- `source_name::String`: Name of source mast (required, no default)
- `min_data_points::Int`: Minimum concurrent data points required (default: 100)
- `max_std_deviation::Float64`: Maximum standard deviation threshold (default: Inf, recommend: 12.5)
- `max_abs_offset::Float64`: Maximum absolute offset threshold (default: Inf, recommend: 45.0)
- `exclude_nan_results::Bool`: Filter out NaN/Inf values (default: true)
"""
@with_kw struct CrossMastDirectionTrainParams
    # Required names (no defaults)
    target_name::String
    source_name::String
    
    # Data quality filters (with defaults)
    min_data_points::Int = 100
    max_std_deviation::Float64 = Inf         # recommend: 12.5
    max_abs_offset::Float64 = Inf            # recommend: 45.0
    exclude_nan_results::Bool = true
end

end # module
```

### Phase 2: Analysis Components
**Location: TrainReconstructCross/ directory** (Implementation logic only)

#### File: `TrainReconstructCross/DataCoverage.jl`
```julia
# Note: MastPairCoverage struct should be in Types/CrossMastAnalysisResults.jl
# This file contains only the analysis functions

function analyze_mast_pair_coverage(target_ts::TimeSeriesData, source_ts::TimeSeriesData)::Union{MastPairCoverage, Nothing}
    # Find highest wind speed sensors for each mast
    # Return nothing if no wind speed sensors found in either mast
    # Get valid timestamps using dropmissing for highest sensors
    # Return MastPairCoverage with zeros if no valid timestamps for sensors
    # Find intersection of valid timestamps between masts
    # Return nothing if no overlapped timestamps exist
    # Calculate coverage statistics based on overlapped timestamps
    # Return MastPairCoverage with detailed analysis
end
```

#### File: `TrainReconstructCross/CrossMastSpeedCorrelation.jl`
```julia
# Analysis, training, and reconstruction functions for wind speed cross-mast models
# Uses unified types from Types/CrossMastSpeedModels.jl, Types/CrossMastTrainParams.jl

function analyze_windspeed_correlations(target_ts::TimeSeriesData, source_ts::TimeSeriesData)::Vector{CrossMastSpeedPair}
    # Find all wind speed sensor pairs between masts
    # For each pair:
    #   - Extract concurrent data points (minimum 100 points required)
    #   - Calculate Pearson correlation
    #   - Fit linear regression: target = slope * source + intercept
    #   - Calculate R², RMSE, and other statistics
    #   - Create CrossMastSpeedPair with all metrics including data_points
    # Return unified results that can be used directly for both analysis and model training
end

function train(::Type{CrossMastSpeedModel}, params::CrossMastSpeedTrainParams, 
               target_ts::TimeSeriesData, source_ts::TimeSeriesData)::CrossMastSpeedModel
    # Use existing analyze_windspeed_correlations function
    # Apply filtering based on params (min_correlation, min_r_squared, etc.)
    # No conversion step needed - analysis results ARE model components
    # Return complete CrossMastSpeedModel with qualified pairs
end

function reconstruct(model::CrossMastSpeedModel, source_ts::TimeSeriesData)::TimeSeriesData
    # Apply trained model to reconstruct target wind speeds from source data
    # For each pair in model.pairs:
    #   - Apply linear regression: target = slope * source + intercept
    #   - Only reconstruct missing values (don't override existing)
    #   - Handle missing values and bounds validation appropriately
    # Return reconstructed TimeSeriesData for target mast
end
```

#### File: `TrainReconstructCross/CrossMastDirectionAnalysis.jl`
```julia
# Analysis, training, and reconstruction functions for wind direction cross-mast models
# Uses unified types from Types/CrossMastDirectionModels.jl, Types/CrossMastTrainParams.jl

function analyze_winddirection_differences(target_ts::TimeSeriesData, source_ts::TimeSeriesData)::Vector{CrossMastDirectionPair}
    # Find all wind direction sensor pairs between masts
    # For each pair:
    #   - Extract concurrent data points (minimum 100 points required)
    #   - Calculate direction differences (handling circular nature with normalize_direction)
    #   - Calculate mean offset and standard deviation using circular statistics
    #   - Count valid data points
    #   - Create CrossMastDirectionPair with all metrics including data_points
    # Return unified results that can be used directly for both analysis and model training
end

function train(::Type{CrossMastDirectionModel}, params::CrossMastDirectionTrainParams,
               target_ts::TimeSeriesData, source_ts::TimeSeriesData)::CrossMastDirectionModel
    # Use existing analyze_winddirection_differences function
    # Apply filtering based on params (max_std_deviation, max_abs_offset, etc.)
    # No conversion step needed - analysis results ARE model components
    # Return complete CrossMastDirectionModel with qualified pairs
end

function reconstruct(model::CrossMastDirectionModel, source_ts::TimeSeriesData)::TimeSeriesData
    # Apply trained model to reconstruct target wind directions from source data
    # For each pair in model.pairs:
    #   - Apply offset correction: target = normalize_direction(source + offset)
    #   - Handle 0°/360° boundary crossing with proper circular wrapping
    #   - Only reconstruct missing values (don't override existing)
    #   - Handle missing values appropriately
    # Return reconstructed TimeSeriesData for target mast
end
```

#### File: `TrainReconstructCross/CrossMastSummary.jl`
```julia
# Summary statistics and high-elevation filtering functions for cross-mast analysis
# Separated from analysis modules for cleaner architecture and reusability

function summarize_correlations(results::Vector{CrossMastSpeedPair})::CorrelationSummary
    # Create summary statistics from wind speed correlation analysis results
    # Calculate total pairs, high-elevation pairs, best/average correlations
    # Return CorrelationSummary struct with all metrics
end

function summarize_direction_analysis(results::Vector{CrossMastDirectionPair})::DirectionSummary
    # Create summary statistics from direction analysis results
    # Calculate total pairs, high-elevation pairs, best/average std deviations
    # Return DirectionSummary struct with all metrics
end

function get_best_high_elevation_correlation(results::Vector{CrossMastSpeedPair})::Float64
    # Filter results for sensors ≥120m height
    # Return maximum correlation among qualified sensors
    # Used for model selection criteria
end

function get_best_high_elevation_direction_std(results::Vector{CrossMastDirectionPair})::Float64
    # Filter results for sensors ≥120m height
    # Return minimum standard deviation among qualified sensors
    # Used for model selection criteria
end

# Helper functions for high-elevation filtering (≥120m sensors)
# Centralized logic for consistent high-elevation criteria across all analysis types
```

### Phase 3: Model Saving and Reporting
**Focus: Model persistence and report generation infrastructure**

#### Model Saving Functions
**Location: TrainReconstructCross/ directory** (Implementation logic only)

##### Model Persistence Functions (New Implementation Needed)
```julia
# Functions to save trained models to JLD2 files during train command execution

function save_speed_model(model::CrossMastSpeedModel, output_dir::String, 
                         target_name::String, source_name::String)::String
    # Create directory structure: output_dir/cross-mast-models/target/source/
    # Save model using JLD2 to windspeed.jld2
    # Return absolute path to saved model file
end

function save_direction_model(model::CrossMastDirectionModel, output_dir::String,
                            target_name::String, source_name::String)::String  
    # Create directory structure: output_dir/cross-mast-models/target/source/
    # Save model using JLD2 to winddirection.jld2
    # Return absolute path to saved model file
end
```

#### Inline TOML Serialization
**Location: Integrated into TrainReconstructCrossCommand.jl** (Simplified approach)

##### TOML Generation (Simplified Implementation)
```julia
# Inline function in main command - leverages existing to_dict infrastructure

function save_train_results_toml(results::Vector{MastPairAnalysisResult}, output_path::String)
    # Trivial implementation using existing to_dict methods:
    # 1. Create metadata dictionary (timestamp, counts)
    # 2. Convert results: [to_dict(result) for result in results]
    # 3. Write TOML file using TOML.jl
    # Total implementation: ~15 lines of code
end
```

#### Report Generation Module
**Location: Standalone module in src/CrossMastReporting/** (Separate reusable module)

**Architecture Decision**: Report generation is now a separate Julia module for:
- **Reusability**: Can be used by multiple cross-mast commands (analyze, reconstruct, etc.)
- **Modularity**: Clean separation of analysis logic vs presentation layer
- **Maintainability**: Visualization and reporting logic centralized
- **Extensibility**: Easy to add new report types or visualization formats

##### File: `src/CrossMastReporting/ReportGeneration.jl`
```julia
module CrossMastReporting

using AlgebraOfGraphics, CairoMakie
using ...Types.CrossMastAnalysisResults: MastPairAnalysisResult, CorrelationSummary, DirectionSummary

export generate_typst_report, create_correlation_matrix_plot, create_coverage_timeline_plot, create_direction_differences_plot

function generate_typst_report(results::Vector{MastPairAnalysisResult}, output_dir::String)
    # Create comprehensive Typst analysis report
    # Include sections:
    #   - Executive summary table
    #   - Correlation analysis with matrices and scatter plots
    #   - Direction difference analysis with charts
    #   - Data coverage timeline
    #   - Model quality statistics
    #   - Recommendations for model selection
end

function create_correlation_matrix_plot(results::Vector{MastPairAnalysisResult})::String
    # Generate correlation heatmap for all mast pairs using AlgebraOfGraphics
    # Focus on ≥120m sensors with high-elevation filtering
    # Use color coding for correlation strength (0.0-1.0 scale)
    # Save as PNG with CairoMakie backend, return file path
end

function create_coverage_timeline_plot(results::Vector{MastPairAnalysisResult})::String
    # Generate timeline showing overlap periods between masts
    # Visual representation of concurrent data availability
    # Use AlgebraOfGraphics for clean timeline visualization
    # Save as PNG, return file path
end

function create_direction_differences_plot(results::Vector{MastPairAnalysisResult})::String
    # Generate charts showing direction offset and std deviation
    # Highlight which pairs meet selection criteria (≤12.5° std dev)
    # Use scatter plots with color coding for quality
    # Save as PNG, return file path
end

end # module
```

##### File: `src/CrossMastReporting/TypstTemplates.jl`
```julia
# Typst template generation functions
# Separate file for template management and content generation

function create_executive_summary_template(results::Vector{MastPairAnalysisResult})::String
    # Generate Typst template for executive summary section
    # Include qualification statistics and key metrics table
end

function create_correlation_analysis_template(results::Vector{MastPairAnalysisResult}, chart_paths::Dict{String, String})::String
    # Generate Typst template for correlation analysis section
    # Include charts and detailed statistics tables
end

function create_direction_analysis_template(results::Vector{MastPairAnalysisResult}, chart_paths::Dict{String, String})::String
    # Generate Typst template for direction analysis section
    # Include offset/std deviation analysis and visualizations
end
```

### Phase 4: Main Command Implementation
**Location: TrainReconstructCross/ directory**

#### File: `TrainReconstructCross/TrainReconstructCrossCommand.jl`
```julia
# Uses all types from Types/ and functions from other TrainReconstructCross/ modules

function execute(config_path::String)
    println("Starting cross-mast training...")
    
    # 1. Load and validate configuration
    config = load_train_config(config_path)
    project_dir = dirname(config_path)
    println("Loaded configuration with $(length(config.masts)) masts")
    
    # 2. Create output directory structure
    mkpath(config.train.output_dir)
    mkpath(joinpath(config.train.output_dir, "cross-mast-models"))
    mkpath(joinpath(config.train.output_dir, "charts"))
    
    # 3. Load all mast time series data
    mast_data = load_all_mast_data(config.masts, project_dir)
    println("Loaded time series data for $(length(mast_data)) masts")
    
    # 4. Analyze all mast pairs (N² combinations)
    analysis_results = Vector{MastPairAnalysisResult}()
    total_pairs = length(config.masts) * (length(config.masts) - 1)
    pair_count = 0
    
    for target_mast in config.masts
        for source_mast in config.masts
            if target_mast.name != source_mast.name
                pair_count += 1
                println("Training pair $pair_count/$total_pairs: $(target_mast.name) <- $(source_mast.name)")
                
                result = train_mast_pair(
                    mast_data[target_mast.name], 
                    mast_data[source_mast.name],
                    target_mast.name,
                    source_mast.name,
                    config.train.output_dir
                )
                
                # Only add results if analysis was successful
                if !isnothing(result)
                    push!(analysis_results, result)
                end
            end
        end
    end
    
    # 5. Save machine-readable results
    results_path = joinpath(config.train.output_dir, "train-results.toml")
    save_train_results_toml(analysis_results, results_path)
    println("Saved training results to: $results_path")
    
    # 6. Generate human-readable report
    generate_typst_report(analysis_results, config.train.output_dir)
    println("Generated Typst report in: $(config.train.output_dir)")
    
    # 7. Summary statistics
    qualified_speed_pairs = count(r -> r.coverage.overlap_days >= 120.0 && 
                                       r.windspeed_summary.best_high_elevation_correlation >= 0.7, 
                                 analysis_results)
    qualified_direction_pairs = count(r -> r.coverage.overlap_days >= 120.0 && 
                                          r.winddirection_summary.best_high_elevation_std <= 12.5, 
                                     analysis_results)
    
    println("\nTraining Summary:")
    println("  Total mast pairs trained: $(length(analysis_results))")
    println("  Qualified for wind speed reconstruction: $qualified_speed_pairs")
    println("  Qualified for wind direction reconstruction: $qualified_direction_pairs")
    println("\nCross-mast training completed successfully!")
end

function train_mast_pair(target_ts::TimeSeriesData, source_ts::TimeSeriesData, 
                          target_name::String, source_name::String, 
                          output_dir::String)::Union{MastPairAnalysisResult, Nothing}
    
    # 1. Data coverage analysis
    coverage = analyze_mast_pair_coverage(target_ts, source_ts)
    
    # Handle case where no coverage analysis is possible
    if isnothing(coverage)
        println("  Coverage: No analysis possible (no wind speed sensors or no overlap)")
        return nothing
    end
    
    println("  Coverage: $(round(coverage.overlap_days, digits=1)) days")
    
    # 2. Wind speed correlation analysis
    speed_correlations = analyze_windspeed_correlations(target_ts, source_ts)
    speed_summary = summarize_correlations(speed_correlations)
    println("  Best high-elevation speed correlation: $(round(speed_summary.best_high_elevation_correlation, digits=3))")
    
    # 3. Wind direction analysis
    direction_analysis = analyze_winddirection_differences(target_ts, source_ts)
    direction_summary = summarize_direction_analysis(direction_analysis)
    println("  Best high-elevation direction std: $(round(direction_summary.best_high_elevation_std, digits=1))°")
    
    # 4. Train and save models if sufficient data available
    speed_model_file = nothing
    direction_model_file = nothing
    
    if coverage.overlap_days >= 30.0  # Minimum threshold for training (30 days)
        # Train and save speed model
        speed_model = train_cross_mast_speed_model(target_ts, source_ts, target_name, source_name)
        speed_model_file = save_speed_model(speed_model, output_dir, target_name, source_name)
        
        # Train and save direction model
        direction_model = train_cross_mast_direction_model(target_ts, source_ts, target_name, source_name)
        direction_model_file = save_direction_model(direction_model, output_dir, target_name, source_name)
    end
    
    # 5. Create summary statistics
    speed_summary = summarize_correlations(speed_correlations)
    direction_summary = summarize_direction_analysis(direction_analysis)
    
    return MastPairAnalysisResult(
        target_name, source_name, coverage,
        speed_correlations, direction_analysis,
        speed_summary, direction_summary,
        speed_model_file, direction_model_file
    )
end

function load_all_mast_data(masts::Vector{TrainCrossMast}, project_dir::String)::Dict{String, TimeSeriesData}
    # Load time series data for all masts
    # Return dictionary mapping mast names to TimeSeriesData
    # Handle file loading errors gracefully
end
```

### Phase 5: Additional Command Files
**Location: TrainReconstructCross/ directory**

- `TrainReconstructCross/RecommendTrainReconstructCrossCommand.jl` - Config generator for train command

**Note**: The `recommend reconstruct-cross` command belongs in the ReconstructCross module (separate implementation), not in TrainReconstructCross.

## Expected Output Structure

```
./train-reconstruct-cross/
├── train-results.toml                   # Machine-readable summary for recommend command
├── report.typ                          # Human-readable comprehensive report (Typst source)
├── cross-mast-models/                  # Trained model files
│   ├── Mast1/
│   │   ├── Mast2/
│   │   │   ├── windspeed.jld2          # Speed model: Mast1 <- Mast2
│   │   │   └── winddirection.jld2      # Direction model: Mast1 <- Mast2
│   │   └── Mast3/
│   │       ├── windspeed.jld2          # Speed model: Mast1 <- Mast3
│   │       └── winddirection.jld2      # Direction model: Mast1 <- Mast3
│   ├── Mast2/
│   │   ├── Mast1/
│   │   │   ├── windspeed.jld2          # Speed model: Mast2 <- Mast1
│   │   │   └── winddirection.jld2      # Direction model: Mast2 <- Mast1
│   │   └── Mast3/
│   │       ├── windspeed.jld2          # Speed model: Mast2 <- Mast3
│   │       └── winddirection.jld2      # Direction model: Mast2 <- Mast3
│   └── Mast3/
│       ├── Mast1/
│       │   ├── windspeed.jld2          # Speed model: Mast3 <- Mast1
│       │   └── winddirection.jld2      # Direction model: Mast3 <- Mast1
│       └── Mast2/
│           ├── windspeed.jld2          # Speed model: Mast3 <- Mast2
│           └── winddirection.jld2      # Direction model: Mast3 <- Mast2
└── charts/                             # Analysis visualization
    ├── correlation_matrix.png          # Heatmap of speed correlations
    ├── direction_differences.png       # Direction offset and std analysis
    └── coverage_timeline.png           # Data availability timeline
```

## Key Features

1. **Comprehensive Pairwise Analysis**: Analyzes all possible mast-to-mast relationships
2. **High-Elevation Focus**: Prioritizes sensors ≥120m for selection criteria
3. **Efficient Model Storage**: One model file per mast-pair per variable type
4. **Rich Reporting**: Both machine-readable (TOML) and human-readable (Typst/PDF) outputs
5. **Robust Error Handling**: Graceful handling of missing data and edge cases
6. **Progress Tracking**: Clear progress indicators for long-running analyses
7. **Statistical Rigor**: Proper correlation analysis and regression modeling

## Integration Points

### Command Dependencies
- **Input**: Generated by `recommend train-reconstruct-cross` command (same module)
- **Output**: Consumed by `recommend reconstruct-cross` command (ReconstructCross module)
- **Dependencies**: Leverages existing TimeSeriesData, SensorColumn, and other core types

### Module Boundaries
- **TrainReconstructCross Module**: Contains this train command and its recommend command
- **ReconstructCross Module**: Contains the reconstruct commands that consume this output
- **Types/ Directory**: Contains all struct definitions shared across modules

### CLI Integration
- **Registration**: Command registered as `train reconstruct-cross` in CleanMastCli.jl
- **Module Import**: TrainReconstructCross and CrossMastReporting modules added to CleanMastProject.jl
- **Command Export**: TrainReconstructCrossCommand.execute function exported
- **Dependencies**: 
  - Typst for report generation
  - AlgebraOfGraphics.jl for plotting (grammar of graphics)
  - CairoMakie.jl for PNG output backend

This implementation provides a comprehensive training engine that generates all necessary artifacts for intelligent cross-mast model selection while maintaining efficiency and robustness.

## CLI Integration Implementation

### Required Changes to Existing Files

#### 1. `src/CleanMastProject.jl`
```julia
# Add to includes section
include("TrainReconstructCross/TrainReconstructCrossCommand.jl")
include("TrainReconstructCross/RecommendTrainReconstructCrossCommand.jl")

# Add to exports
export TrainReconstructCrossCommand, RecommendTrainReconstructCrossCommand
```

#### 2. `src/CleanMastCli.jl`
```julia
# Add to command definitions
@add_arg_table! s begin
    "recommend"
        action = :command
        help = "Recommend configuration for various commands"
        @add_arg_table! begin
            "train-reconstruct-cross"
                action = :command
                help = "Generate train-reconstruct-cross.toml configuration"
                # Add specific arguments for recommend command
        end
    "train"
        action = :command
        help = "Train models for various purposes"
        @add_arg_table! begin
            "reconstruct-cross"
                action = :command
                help = "Train cross-mast relationships and models"
                "config"
                    arg_type = String
                    required = true
                    help = "Path to train-reconstruct-cross.toml configuration file"
        end
end

# Add to command execution logic
if parsed_args["train"]["reconstruct-cross"] !== nothing
    config_path = parsed_args["train"]["reconstruct-cross"]["config"]
    TrainReconstructCrossCommand.execute(config_path)
end
```

#### 3. Module Structure in CleanMastProject.jl
```julia
# Module entry point in src/CleanMastProject.jl

# Cross-mast training module (specific to train command)
module TrainReconstructCross
  include("./TrainReconstructCross/DataCoverage.jl")
  include("./TrainReconstructCross/CrossMastSpeedCorrelation.jl")
  include("./TrainReconstructCross/CrossMastDirectionAnalysis.jl")
  include("./TrainReconstructCross/CrossMastSummary.jl")
  include("./TrainReconstructCross/ResultsSerialization.jl")  # Phase 3
  # Command files to be added in Phase 4
  export DataCoverage, CrossMastSpeedCorrelation, CrossMastDirectionAnalysis, CrossMastSummary, ResultsSerialization
end

# Cross-mast reporting module (reusable across commands)
module CrossMastReporting
  include("./CrossMastReporting/ReportGeneration.jl")
  include("./CrossMastReporting/TypstTemplates.jl")
  export ReportGeneration, TypstTemplates
end

export TrainReconstructCross, CrossMastReporting
```

## Next Steps (Updated: 2024-12-11)

### ✅ **TRAIN RECONSTRUCT-CROSS FULLY COMPLETED**
**Status**: 🎉 **ALL PHASES IMPLEMENTED AND WORKING** 🎉

1. **Phase 1**: ✅ **COMPLETED** - Core data structures in `Types/`
   - [x] Create `Types/TrainReconstructCrossConfig.jl` - ✅ 2024-12-20
   - [x] Create `Types/CrossMastSpeedModels.jl` - ✅ 2024-12-20
   - [x] Create `Types/CrossMastDirectionModels.jl` - ✅ 2024-12-20
   - [x] Create `Types/CrossMastAnalysisResults.jl` - ✅ 2024-12-20
   - [x] Create `Types/CrossMastTrainParams.jl` - ✅ 2024-12-20

2. **Phase 2**: ✅ **COMPLETED** - Analysis components in `TrainReconstructCross/`
   - [x] Implement `DataCoverage.jl` - ✅ 2024-12-20
   - [x] Implement `CrossMastSpeedCorrelation.jl` with train/reconstruct - ✅ 2024-12-20
   - [x] Implement `CrossMastDirectionAnalysis.jl` with train/reconstruct - ✅ 2024-12-20
   - [x] Create `CrossMastSummary.jl` (separated for cleaner architecture) - ✅ 2024-12-20
   - [x] Major refactoring: struct consolidation and summary separation - ✅ 2024-12-20

3. **Phase 3**: ✅ **COMPLETED** - Model Saving and Results Management
   - [x] Implement `save_speed_model()` function (JLD2 persistence) - ✅ 2024-12-11
   - [x] Implement `save_direction_model()` function (JLD2 persistence) - ✅ 2024-12-11
   - [x] Implement `save_train_results_toml()` (inline TOML serialization) - ✅ 2024-12-11

4. **Phase 4**: ✅ **COMPLETED** - Command Implementation
   - [x] Implement `TrainReconstructCross/TrainReconstructCrossCommand.jl` - ✅ 2024-12-11
     - [x] Main training workflow orchestration - ✅ 2024-12-11
     - [x] Model saving integration - ✅ 2024-12-11
     - [x] Inline TOML serialization (using existing to_dict methods) - ✅ 2024-12-11
   - [x] Implement `TrainReconstructCross/RecommendTrainReconstructCrossCommand.jl` - ✅ 2024-12-11
   - [x] Add CLI command registration in `CleanMastCli.jl` - ✅ 2024-12-11
   - [x] Update `CleanMastProject.jl` to include TrainReconstructCross module - ✅ 2024-12-11

5. **Integration Status**: ✅ **FULLY WORKING**
   - [x] Package compiles successfully - ✅ 2024-12-11
   - [x] CLI commands working: `recommend train-reconstruct-cross` - ✅ 2024-12-11
   - [x] CLI commands working: `train reconstruct-cross` - ✅ 2024-12-11
   - [x] Complete workflow: recommend → train → save models → save results - ✅ 2024-12-11

### 🎯 **NEXT PHASE: RECONSTRUCT CROSS-MASTS**
**Status**: ❌ **NOT YET IMPLEMENTED** - See `plan-reconstruct-cross.md`

The training system is complete and ready to use. The next major implementation is the reconstruction commands:
- `recommend reconstruct-cross` - Generate reconstruction config from training results
- `process reconstruct-cross` - Execute actual data reconstruction using trained models

**Note**: CrossMastReporting module (visualization/Typst reports) is optional and can be implemented later for enhanced reporting.

### 🏆 Architecture Quality Achieved
- **Clean Type Organization**: All structs properly organized in Types/ directory
- **Unified Design**: Eliminated redundant structs (4 → 2), preserved data_points information
- **Modular Architecture**: Summary functions separated for reusability, reporting as standalone module
- **Type Safety**: Comprehensive parameter structs for configurable training
- **Error Handling**: Robust handling of edge cases and missing data
- **Performance**: No unnecessary object conversion between analysis and model training
- **Optimized Summary Structs**: Removed redundant average fields, focused on actionable metrics
- **Simplified Serialization**: Leverages existing to_dict infrastructure, eliminates unnecessary modules
- **Separate Reporting Module**: CrossMastReporting module for reusable visualization and report generation

### Key Architecture Notes
- **Struct Consolidation**: CrossMastSpeedPair and CrossMastDirectionPair serve both as analysis results AND model components
- **Summary Separation**: Statistics and filtering logic centralized in CrossMastSummary.jl
- **Direct Usage**: Analysis results can be used directly for model training (no conversion needed)
- **Optimized Summary Structs**: Focus on actionable metrics (best correlations, high-elevation averages, essential std deviations)
- **Serialization Simplification**: Inline TOML generation leverages existing to_dict methods (no extra module needed)
- **Modular Reporting**: CrossMastReporting as separate module for reusability across cross-mast commands
- **Clean Separation**: Analysis logic (TrainReconstructCross) vs presentation layer (CrossMastReporting)
- **Extensible Design**: Easy to add new analysis types, summary statistics, or visualization formats

### Review Points Completed
- ✅ Phase 1: Type designs reviewed and implemented with @with_kw constructors
- ✅ Phase 2: Analysis algorithms validated with train/reconstruct functions
- 🔄 Ready for Phase 3: Results management implementation 