# Cross-Mast Reconstruction - Reconstruct Commands Implementation Plan

## 📋 Document Overview

### Purpose
This document outlines the implementation plan for the **recommend reconstruct-cross** and **process reconstruct-cross** commands. These commands complete the cross-mast reconstruction workflow by providing intelligent reconstruction recommendations and executing priority-based data reconstruction.

### Context
This plan builds on the **fully completed** train reconstruct-cross command implementation. The workflow is:

1. ✅ `recommend train-reconstruct-cross` → produces `train-reconstruct-cross.toml` (COMPLETED)
2. ✅ `train reconstruct-cross` → produces `train-results.toml` + model files (COMPLETED)
3. ✅ `recommend reconstruct-cross` → reads `train-results.toml` → produces `reconstruct-cross.toml` (COMPLETED - commit 6e1607b)
4. 🎯 `process reconstruct-cross` → reads `reconstruct-cross.toml` → produces reconstructed data (NEXT PRIORITY)

**Current Status**: The training system is fully operational with working CLI commands. All analysis components, model training, and model saving are implemented and tested. The reconstruction functions (`reconstruct()`) are also implemented in the analysis modules and ready to use.

## Command Specifications

### Command 1: `recommend reconstruct-cross`

**Purpose**: Generate intelligent reconstruction configuration with priority-based mast selection

**Input**: `train-results.toml` (from train command)
**Output**: `reconstruct-cross.toml` (configuration for reconstruct command)

**Core Logic**: 
- For each mast, find the best source mast with correlation >0.7 at ≥120m sensors
- Create priority queue: masts with better correlations reconstruct first
- Include fallback options (2nd, 3rd best correlations) for robustness
- Only recommend qualified pairs (≥120 days overlap, high correlation)

### Command 2: `process reconstruct-cross`

**Purpose**: Execute cross-mast data reconstruction using trained models

**Input**: `reconstruct-cross.toml` (configuration file)
**Output**: Reconstructed time series files for target masts

**Core Logic**:
- Load trained models for each reconstruction job
- Apply reconstruction in priority order (best correlations first)
- Only fill missing data points (preserve existing measurements)
- Generate reconstruction reports and quality metrics

## Implementation Architecture

### Phase 1: Core Data Structures ✅ **COMPLETED**
**Location: Types/ directory**
**Status**: Implemented in commit 6e1607b

#### File: `Types/ReconstructCrossConfig.jl`
```julia
module ReconstructCrossConfig

using Parameters
using Dates
using ..TimeSeriesProcessing: TimeSeriesSource

export ReconstructCrossConfiguration, ReconstructCrossSettings, ReconstructionJob, ReconstructionPriority

"""
    ReconstructionJob

Single reconstruction operation: target mast ← source mast using trained model.
"""
@with_kw struct ReconstructionJob
    target_mast::String
    source_mast::String
    model_dir::String                    # Path to model files (windspeed.jld2, winddirection.jld2)
    priority::Int                        # 1 = highest priority, 2 = secondary, etc.
    speed_correlation::Float64           # Best high-elevation correlation for this pair
    direction_std::Float64               # Best high-elevation std deviation for this pair
    data_coverage_days::Float64          # Days of overlapping data available
    variables::Vector{String}            # ["windspeed", "winddirection"] or subset
end

"""
    ReconstructionPriority

Priority grouping for reconstruction order. Masts with better correlations reconstruct first.
"""
@with_kw struct ReconstructionPriority
    priority_level::Int                  # 1 = best correlations, 2 = good, 3 = acceptable
    min_correlation::Float64             # Minimum correlation for this priority level
    max_direction_std::Float64           # Maximum direction std for this priority level
    jobs::Vector{ReconstructionJob}      # All jobs at this priority level
end

"""
    ReconstructCrossSettings

Configuration settings for reconstruction execution.
"""
@with_kw struct ReconstructCrossSettings
    output_dir::String = "./reconstruct-cross"
    preserve_existing::Bool = true       # Only fill missing data, don't override existing
    min_confidence::Float64 = 0.7        # Minimum correlation to attempt reconstruction
    max_direction_uncertainty::Float64 = 12.5  # Maximum direction std deviation (degrees)
    generate_reports::Bool = true        # Generate reconstruction quality reports
    backup_originals::Bool = true        # Create backup of original files before reconstruction
end

"""
    ReconstructCrossConfiguration

Complete configuration for cross-mast reconstruction command.
"""
@with_kw struct ReconstructCrossConfiguration
    # Input data sources for each mast (original time series)
    masts::Vector{ReconstructCrossMast}
    
    # Reconstruction job queue (ordered by priority)
    reconstruction_priorities::Vector{ReconstructionPriority}
    
    # Execution settings
    settings::ReconstructCrossSettings
    
    # Metadata from training
    training_metadata::Dict{String, Any}
end

"""
    ReconstructCrossMast

Input specification for a mast that may be reconstructed.
"""
@with_kw struct ReconstructCrossMast
    name::String
    input::TimeSeriesSource              # Original data source
    output::Union{TimeSeriesSource, Nothing} = nothing  # Where to save reconstructed data (optional)
end

# Serialization methods (from_dict/to_dict) following project patterns
function from_dict(::Type{ReconstructionJob}, dict::Dict{String, Any})::ReconstructionJob
    # Implementation: convert dict to ReconstructionJob struct
end

function to_dict(job::ReconstructionJob)::Dict{String, Any}
    # Implementation: convert ReconstructionJob to dict for TOML
end

function from_dict(::Type{ReconstructCrossConfiguration}, dict::Dict{String, Any})::ReconstructCrossConfiguration
    # Implementation: convert dict to full configuration
end

function to_dict(config::ReconstructCrossConfiguration)::Dict{String, Any}
    # Implementation: convert configuration to dict for TOML
end

end # module
```

#### File: `Types/ReconstructCrossResults.jl`
```julia
module ReconstructCrossResults

using Parameters
using Dates
using ..SensorColumns: SensorColumn

export ReconstructionJobResult, ReconstructionSummary, QualityMetrics

"""
    QualityMetrics

Quality assessment metrics for a single sensor reconstruction.
"""
@with_kw struct QualityMetrics
    sensor::SensorColumn
    filled_points::Int                   # Number of missing values filled
    total_missing::Int                   # Total missing values before reconstruction
    fill_percentage::Float64             # Percentage of missing data filled
    model_correlation::Float64           # Correlation used for this reconstruction
    model_rmse::Union{Float64, Nothing}  # RMSE for speed models (nothing for direction)
    reconstruction_start::DateTime       # First reconstructed timestamp
    reconstruction_end::DateTime         # Last reconstructed timestamp
end

"""
    ReconstructionJobResult

Results from executing a single reconstruction job.
"""
@with_kw struct ReconstructionJobResult
    job::ReconstructionJob              # Original job specification
    execution_start::DateTime           # When reconstruction started
    execution_end::DateTime             # When reconstruction completed
    success::Bool                       # Whether reconstruction completed successfully
    error_message::Union{String, Nothing} = nothing  # Error details if failed
    
    # Quality metrics for each reconstructed sensor
    windspeed_metrics::Vector{QualityMetrics}
    winddirection_metrics::Vector{QualityMetrics}
    
    # Output file paths
    output_file::Union{String, Nothing} = nothing  # Path to reconstructed time series file
    quality_report::Union{String, Nothing} = nothing  # Path to quality assessment report
end

"""
    ReconstructionSummary

Overall summary of entire reconstruction campaign.
"""
@with_kw struct ReconstructionSummary
    campaign_start::DateTime
    campaign_end::DateTime
    total_jobs::Int
    successful_jobs::Int
    failed_jobs::Int
    
    # Aggregate statistics
    total_filled_points::Int             # Total missing values filled across all masts
    total_missing_points::Int            # Total missing values across all masts  
    overall_fill_percentage::Float64     # Overall percentage of missing data filled
    
    # Quality summary
    average_correlation::Float64         # Average correlation of applied models
    best_correlation::Float64            # Best correlation achieved
    worst_correlation::Float64           # Worst correlation applied
    
    # File results
    job_results::Vector{ReconstructionJobResult}
    summary_report::Union{String, Nothing} = nothing  # Path to campaign summary report
end

# Serialization methods
function to_dict(metrics::QualityMetrics)::Dict{String, Any}
    # Implementation: convert quality metrics to dict
end

function to_dict(result::ReconstructionJobResult)::Dict{String, Any}
    # Implementation: convert job result to dict
end

function to_dict(summary::ReconstructionSummary)::Dict{String, Any}
    # Implementation: convert summary to dict for TOML output
end

end # module
```

### Phase 2: Recommend Command Implementation ✅ **COMPLETED**
**Location: ReconstructCross/ directory**
**Status**: Implemented in commit 6e1607b

#### File: `ReconstructCross/RecommendReconstructCrossCommand.jl`
```julia
module RecommendReconstructCrossCommand

export execute

"""
    execute(train_results_path::String, output_dir::String = "./") 

Generate reconstruct-cross.toml configuration from train-results.toml.

# Arguments
- `train_results_path::String`: Path to train-results.toml from train command
- `output_dir::String`: Directory to write reconstruct-cross.toml (default: current directory)

# Algorithm
1. Load and parse train-results.toml
2. Filter qualified mast pairs (correlation ≥0.7, ≥120m sensors, ≥120 days data)
3. For each target mast, find best source mast(s) by correlation
4. Create priority levels: excellent (≥0.9), good (≥0.8), acceptable (≥0.7)
5. Generate reconstruction job queue with fallback options
6. Create complete reconstruct-cross.toml configuration

# Returns
- Path to generated reconstruct-cross.toml file
"""
function execute(train_results_path::String, output_dir::String = "./")::String
    # Implementation details in Phase 2
end

"""
    analyze_reconstruction_opportunities(train_results::Vector{MastPairAnalysisResult})::Dict{String, Vector{ReconstructionCandidate}}

Analyze train results to identify reconstruction opportunities for each mast.

# Arguments  
- `train_results`: Results from train command

# Returns
- Dictionary mapping target mast name to sorted list of reconstruction candidates (best correlation first)
"""
function analyze_reconstruction_opportunities(train_results::Vector{MastPairAnalysisResult})::Dict{String, Vector{ReconstructionCandidate}}
    # Implementation: analyze which masts can reconstruct from which sources
end

"""
    ReconstructionCandidate

Internal struct for recommendation analysis.
"""
struct ReconstructionCandidate
    source_mast::String
    speed_correlation::Float64
    direction_std::Float64  
    data_coverage_days::Float64
    model_paths::Dict{String, String}    # "windspeed" => path, "winddirection" => path
    qualification_score::Float64         # Combined quality score for ranking
end

"""
    create_priority_levels(candidates::Dict{String, Vector{ReconstructionCandidate}})::Vector{ReconstructionPriority}

Group reconstruction jobs into priority levels based on correlation quality.

# Arguments
- `candidates`: Reconstruction candidates for each target mast

# Returns  
- Vector of priority levels (1=excellent, 2=good, 3=acceptable)
"""
function create_priority_levels(candidates::Dict{String, Vector{ReconstructionCandidate}})::Vector{ReconstructionPriority}
    # Implementation: group by correlation thresholds (0.9, 0.8, 0.7)
end

"""
    validate_model_availability(candidates::Vector{ReconstructionCandidate}, train_results_dir::String)::Vector{ReconstructionCandidate}

Verify that required model files exist for each reconstruction candidate.

# Arguments
- `candidates`: Potential reconstruction candidates  
- `train_results_dir`: Directory containing cross-mast-models/ subdirectory

# Returns
- Filtered candidates where both windspeed.jld2 and winddirection.jld2 exist
"""
function validate_model_availability(candidates::Vector{ReconstructionCandidate}, train_results_dir::String)::Vector{ReconstructionCandidate}
    # Implementation: check file existence for model files
end

end # module
```

### Phase 3: Reconstruct Command Implementation ⏳  
**Location: ReconstructCross/ directory**

#### File: `ReconstructCross/ReconstructCrossCommand.jl`
```julia
module ReconstructCrossCommand

export execute

"""
    execute(config_path::String)

Execute cross-mast reconstruction using trained models.

# Arguments
- `config_path::String`: Path to reconstruct-cross.toml configuration file

# Workflow
1. Load configuration and validate inputs
2. Load original time series data for all masts
3. Execute reconstruction jobs in priority order
4. Apply trained models to fill missing data points only
5. Save reconstructed time series files  
6. Generate quality assessment reports
7. Create campaign summary

# Returns
- ReconstructionSummary with complete results
"""
function execute(config_path::String)::ReconstructionSummary
    # Implementation details in Phase 3
end

"""
    execute_reconstruction_job(job::ReconstructionJob, target_ts::TimeSeriesData, source_ts::TimeSeriesData, config::ReconstructCrossConfiguration)::ReconstructionJobResult

Execute a single reconstruction job using trained models.

# Arguments
- `job`: Reconstruction job specification
- `target_ts`: Original target mast time series (to be reconstructed)
- `source_ts`: Source mast time series (reference data)
- `config`: Overall reconstruction configuration

# Algorithm
1. Load trained speed and direction models from job.model_dir
2. Apply speed model: fill missing wind speed values using linear regression
3. Apply direction model: fill missing wind direction values using offset correction
4. Only modify missing/NaN values (preserve existing measurements if config.preserve_existing)
5. Validate reconstructed values (bounds checking, QA rules)
6. Calculate quality metrics for each reconstructed sensor

# Returns
- ReconstructionJobResult with success status and quality metrics
"""
function execute_reconstruction_job(job::ReconstructionJob, target_ts::TimeSeriesData, source_ts::TimeSeriesData, config::ReconstructCrossConfiguration)::ReconstructionJobResult
    # Implementation: load models, apply reconstruction, calculate metrics
end

"""
    apply_speed_reconstruction(target_ts::TimeSeriesData, source_ts::TimeSeriesData, speed_model::CrossMastSpeedModel, preserve_existing::Bool)::Tuple{TimeSeriesData, Vector{QualityMetrics}}

Apply wind speed reconstruction using trained CrossMastSpeedModel.

# Arguments
- `target_ts`: Target time series (will be modified)
- `source_ts`: Source time series (reference)
- `speed_model`: Trained speed correlation model
- `preserve_existing`: If true, only fill missing values

# Algorithm
For each speed sensor pair in model.pairs:
1. Find concurrent timestamps between target and source sensors
2. Identify missing values in target sensor (NaN/missing)
3. Apply linear regression: target = slope * source + intercept
4. Validate reconstructed values (reasonable bounds, positive speeds)
5. Calculate quality metrics (fill percentage, correlation validation)

# Returns
- Modified target_ts with reconstructed speed values
- Vector of QualityMetrics for each reconstructed sensor
"""
function apply_speed_reconstruction(target_ts::TimeSeriesData, source_ts::TimeSeriesData, speed_model::CrossMastSpeedModel, preserve_existing::Bool)::Tuple{TimeSeriesData, Vector{QualityMetrics}}
    # Implementation: apply trained speed models to fill missing data
end

"""
    apply_direction_reconstruction(target_ts::TimeSeriesData, source_ts::TimeSeriesData, direction_model::CrossMastDirectionModel, preserve_existing::Bool)::Tuple{TimeSeriesData, Vector{QualityMetrics}}

Apply wind direction reconstruction using trained CrossMastDirectionModel.

# Arguments  
- `target_ts`: Target time series (will be modified)
- `source_ts`: Source time series (reference)
- `direction_model`: Trained direction offset model
- `preserve_existing`: If true, only fill missing values

# Algorithm
For each direction sensor pair in model.pairs:
1. Find concurrent timestamps between target and source sensors
2. Identify missing values in target sensor (NaN/missing)
3. Apply offset correction: target = normalize_direction(source + offset)
4. Handle 0°/360° boundary crossing properly
5. Validate reconstructed directions (0-360° bounds)
6. Calculate quality metrics (fill percentage, offset validation)

# Returns
- Modified target_ts with reconstructed direction values  
- Vector of QualityMetrics for each reconstructed sensor
"""
function apply_direction_reconstruction(target_ts::TimeSeriesData, source_ts::TimeSeriesData, direction_model::CrossMastDirectionModel, preserve_existing::Bool)::Tuple{TimeSeriesData, Vector{QualityMetrics}}
    # Implementation: apply trained direction models to fill missing data
end

"""
    validate_reconstructed_values(ts::TimeSeriesData, metrics::Vector{QualityMetrics})::Bool

Validate reconstructed time series for quality and consistency.

# Arguments
- `ts`: Reconstructed time series
- `metrics`: Quality metrics from reconstruction

# Validation Checks
1. Speed values: positive, reasonable bounds (0-100 m/s)
2. Direction values: within 0-360° range
3. Temporal consistency: no sudden unrealistic jumps
4. Fill percentage: reasonable amount of data reconstructed
5. Correlation validation: spot-check correlation matches model expectations

# Returns
- True if validation passes, False if quality concerns detected
"""
function validate_reconstructed_values(ts::TimeSeriesData, metrics::Vector{QualityMetrics})::Bool
    # Implementation: quality validation of reconstructed data
end

end # module
```

### Phase 4: Reporting and Quality Assessment ⏳
**Location: ReconstructCross/ directory**

#### File: `ReconstructCross/QualityAssessment.jl`
```julia
module QualityAssessment

export generate_reconstruction_report, create_quality_plots, assess_reconstruction_quality

"""
    generate_reconstruction_report(result::ReconstructionJobResult, output_dir::String)::String

Generate detailed quality assessment report for a single reconstruction job.

# Arguments
- `result`: Results from reconstruction job execution
- `output_dir`: Directory to save report files

# Report Contents
1. Executive summary (fill percentages, correlation validation)
2. Sensor-by-sensor quality metrics table
3. Time series comparison plots (before/after reconstruction)
4. Correlation validation scatter plots
5. Data quality flags and warnings

# Returns
- Path to generated report file (Typst/PDF)
"""
function generate_reconstruction_report(result::ReconstructionJobResult, output_dir::String)::String
    # Implementation: create detailed quality report
end

"""
    create_quality_plots(target_ts::TimeSeriesData, reconstructed_ts::TimeSeriesData, metrics::Vector{QualityMetrics}, output_dir::String)::Vector{String}

Create visualization plots for reconstruction quality assessment.

# Arguments
- `target_ts`: Original target time series
- `reconstructed_ts`: Time series after reconstruction
- `metrics`: Quality metrics for each sensor
- `output_dir`: Directory to save plot files

# Plot Types
1. Time series overlay: original vs reconstructed data
2. Scatter plots: validation of applied correlations
3. Fill coverage timeline: when reconstruction was applied
4. Quality metrics summary charts

# Returns
- Vector of paths to generated plot files (PNG format)
"""
function create_quality_plots(target_ts::TimeSeriesData, reconstructed_ts::TimeSeriesData, metrics::Vector{QualityMetrics}, output_dir::String)::Vector{String}
    # Implementation: create AlgebraOfGraphics visualizations
end

"""
    assess_reconstruction_quality(metrics::Vector{QualityMetrics})::Dict{String, Any}

Assess overall quality of reconstruction results.

# Arguments
- `metrics`: Quality metrics from all reconstructed sensors

# Quality Assessment Criteria
1. Fill percentage: >50% = excellent, 20-50% = good, <20% = poor
2. Correlation validation: within 10% of trained model = good
3. Temporal coverage: consistent throughout period vs sporadic gaps
4. Sensor consistency: similar quality across sensor heights

# Returns
- Dictionary with quality scores, flags, and recommendations
"""
function assess_reconstruction_quality(metrics::Vector{QualityMetrics})::Dict{String, Any}
    # Implementation: analyze reconstruction quality and provide scores
end

end # module
```

### Phase 5: CLI Integration ⏳
**Location: Existing CLI files**

#### Required Changes to `CleanMastCli.jl`
```julia
# Add new command imports
using CleanMastProject.ReconstructCross.RecommendReconstructCrossCommand  
using CleanMastProject.ReconstructCross.ReconstructCrossCommand

# Add recommend command
@cast function recommend_reconstruct_cross(train_results_dir::String, output_dir::String = "./")
    "Generate reconstruct-cross.toml configuration from train results"
    RecommendReconstructCrossCommand.execute(train_results_dir, output_dir)
end

# Add process command  
@cast function process_reconstruct_cross(config_path::String)
    "Execute cross-mast reconstruction using trained models"
    ReconstructCrossCommand.execute(config_path)
end
```

#### Required Changes to `CleanMastProject.jl`
```julia
# Add new module
module ReconstructCross
  include("./ReconstructCross/RecommendReconstructCrossCommand.jl")
  include("./ReconstructCross/ReconstructCrossCommand.jl") 
  include("./ReconstructCross/QualityAssessment.jl")
  
  export RecommendReconstructCrossCommand, ReconstructCrossCommand, QualityAssessment
end

export ReconstructCross
```

## Expected Configuration Files

### Input: `reconstruct-cross.toml` (Generated by recommend command)
```toml
[settings]
output_dir = "./reconstruct-cross"
preserve_existing = true
min_confidence = 0.7
max_direction_uncertainty = 12.5
generate_reports = true
backup_originals = true

[[masts]]
name = "Mast1"
input.data = "./clean/Mast1.csv" 
input.sensors = "./clean/Mast1.sensors.yaml"
output.data = "./reconstruct-cross/Mast1_reconstructed.csv"

[[masts]]
name = "Mast2"
input.data = "./clean/Mast2.csv"
input.sensors = "./clean/Mast2.sensors.yaml"

[[masts]]
name = "Mast3"
input.data = "./clean/Mast3.csv"
input.sensors = "./clean/Mast3.sensors.yaml"

# Priority Level 1: Excellent correlations (≥0.9)
[[reconstruction_priorities]]
priority_level = 1
min_correlation = 0.9
max_direction_std = 8.0

  [[reconstruction_priorities.jobs]]
  target_mast = "Mast1"
  source_mast = "Mast2"
  model_dir = "./train-reconstruct-cross/cross-mast-models/Mast1/Mast2"
  priority = 1
  speed_correlation = 0.92
  direction_std = 6.2
  data_coverage_days = 847.3
  variables = ["windspeed", "winddirection"]

# Priority Level 2: Good correlations (≥0.8)  
[[reconstruction_priorities]]
priority_level = 2
min_correlation = 0.8
max_direction_std = 10.0

  [[reconstruction_priorities.jobs]]
  target_mast = "Mast3"
  source_mast = "Mast1"
  model_dir = "./train-reconstruct-cross/cross-mast-models/Mast3/Mast1"
  priority = 2
  speed_correlation = 0.84
  direction_std = 9.1
  data_coverage_days = 652.1
  variables = ["windspeed", "winddirection"]

[training_metadata]
training_date = "2024-12-20T15:30:00"
total_mast_pairs = 6
qualified_speed_pairs = 4
qualified_direction_pairs = 3
train_results_file = "./train-reconstruct-cross/train-results.toml"
```

## Expected Output Structure

### Output from `recommend reconstruct-cross`
```
./
├── reconstruct-cross.toml           # Generated configuration file
└── reconstruction-plan.md           # Human-readable recommendation report
```

### Output from `reconstruct-cross`  
```
./reconstruct-cross/
├── Mast1_reconstructed.csv         # Reconstructed time series
├── Mast3_reconstructed.csv         # Reconstructed time series  
├── originals/                      # Backup of original files (if enabled)
│   ├── Mast1.csv
│   └── Mast3.csv
├── quality-reports/               # Quality assessment reports
│   ├── Mast1_quality.typ
│   ├── Mast1_quality.pdf
│   ├── Mast3_quality.typ
│   └── Mast3_quality.pdf
├── plots/                         # Quality assessment plots
│   ├── Mast1_timeseries.png
│   ├── Mast1_correlation_validation.png
│   ├── Mast3_timeseries.png
│   └── Mast3_correlation_validation.png
├── reconstruction-summary.toml     # Machine-readable campaign results
└── campaign-report.typ            # Human-readable campaign summary
```

## Implementation Priority and Dependencies

### Implementation Order
1. **Phase 1**: Core data structures (Types/ files) 
2. **Phase 2**: Recommend command (analysis and configuration generation)
3. **Phase 3**: Reconstruct command (model application and data reconstruction)
4. **Phase 4**: Quality assessment and reporting
5. **Phase 5**: CLI integration and testing

### Key Dependencies
- **Training Output**: Requires completed `train reconstruct-cross` command ✅ **AVAILABLE**
- **Model Loading**: Uses existing CrossMastSpeedModel and CrossMastDirectionModel types ✅ **AVAILABLE**
- **Time Series**: Leverages existing TimeSeriesData and related infrastructure ✅ **AVAILABLE**
- **Serialization**: Uses existing from_dict/to_dict patterns ✅ **AVAILABLE**
- **Reconstruction Functions**: Uses existing `reconstruct()` functions ✅ **AVAILABLE**

### Integration Points
- **Input**: Consumes `train-results.toml` from TrainReconstructCross module ✅ **AVAILABLE**
- **Models**: Loads JLD2 model files created by train command ✅ **AVAILABLE**
- **Reconstruction**: Uses existing `reconstruct()` functions from CrossMastSpeedCorrelation and CrossMastDirectionAnalysis ✅ **AVAILABLE**
- **Output**: Produces reconstructed time series compatible with existing analysis commands
- **Reporting**: Can reuse visualization patterns from AnalyzeReconstructCross module

## Current Implementation Status

### ✅ **FOUNDATION READY**
All prerequisites for reconstruction are implemented and working:

- **Training System**: Complete workflow from recommend → train → save models ✅
- **Model Types**: CrossMastSpeedModel, CrossMastDirectionModel with serialization ✅
- **Reconstruction Functions**: `reconstruct()` methods implemented and tested ✅
- **Infrastructure**: TimeSeriesData, SensorColumn, from_dict/to_dict patterns ✅
- **CLI Framework**: Comonicon-based command structure established ✅

### ❌ **MISSING COMPONENTS**
The following need to be implemented:

1. **ReconstructCross Module**: New directory `src/ReconstructCross/`
2. **Configuration Types**: `Types/ReconstructCrossConfig.jl` and `Types/ReconstructCrossResults.jl`
3. **Recommend Command**: `ReconstructCross/RecommendReconstructCrossCommand.jl`
4. **Process Command**: `ReconstructCross/ReconstructCrossCommand.jl`
5. **CLI Integration**: Add commands to `CleanMastCli.jl`

## Next Steps

### Phase 1 Implementation (Types)
1. Create `Types/ReconstructCrossConfig.jl` with complete type definitions
2. Create `Types/ReconstructCrossResults.jl` with result types
3. Add serialization methods (from_dict/to_dict) following project patterns
4. Update `CleanMastProject.jl` to include new Types

### Phase 2 Implementation (Recommend Command)
1. Create `ReconstructCross/` directory structure
2. Implement `RecommendReconstructCrossCommand.jl` with train results analysis
3. Implement priority-based job queue generation
4. Test recommend command with existing train results

### Phase 3 Implementation (Process Command)
1. Implement `ReconstructCrossCommand.jl` with model loading and reconstruction
2. Implement quality assessment and validation
3. Add CLI command registration
4. Test complete workflow

### Quality Validation Strategy
1. **Model Validation**: Verify trained models exist and load correctly
2. **Configuration Validation**: Ensure generated configs are valid and executable
3. **Reconstruction Validation**: Spot-check reconstructed correlations match training
4. **Quality Metrics**: Validate fill percentages and reconstruction coverage
5. **Integration Testing**: Full workflow from train → recommend → reconstruct

This plan provides a comprehensive framework for intelligent, priority-based cross-mast reconstruction that leverages the already-completed training infrastructure.

---

## 🎉 **UPDATE 2025-08-11: RECOMMEND COMMAND COMPLETED**

### ✅ **Phase 1-2 Implementation Status**
**Commit**: 6e1607b
**Status**: Fully implemented and working

#### Completed Components:
1. **Types/ReconstructCrossConfig.jl** ✅
   - ReconstructionJob, ReconstructionPriority, ReconstructCrossSettings
   - ReconstructCrossMast, ReconstructCrossConfiguration
   - Complete serialization methods (from_dict/to_dict)

2. **Types/ReconstructCrossResults.jl** ✅
   - QualityMetrics, ReconstructionJobResult, ReconstructionSummary
   - Complete serialization methods for future process command

3. **ReconstructCross/RecommendReconstructCrossCommand.jl** ✅
   - Intelligent model selection with qualification criteria
   - Priority-based job generation (excellent ≥0.9, good ≥0.8, acceptable ≥0.7)
   - Model availability validation
   - Complete TOML configuration generation

4. **CLI Integration** ✅
   - Command registered in CleanMastCli.jl
   - Module exported in CleanMastProject.jl

#### Working Command:
```bash
julia --project=. bin/CleanMast.jl recommend reconstruct-cross train-results.toml [output-dir]
```

---

## 🎯 **NEXT PRIORITY: PROCESS RECONSTRUCT-CROSS COMMAND**

### Phase 3: Process Command Implementation ❌ **NEXT TO IMPLEMENT**
**Location: ReconstructCross/ directory**

#### Required Implementation: `ReconstructCross/ProcessReconstructCrossCommand.jl`

**Core Algorithm**:
1. Load reconstruct-cross.toml configuration
2. Load original time series data for all masts
3. Execute reconstruction jobs in priority order
4. Apply trained models to fill missing data points only
5. Save reconstructed time series files
6. Generate quality assessment reports
7. Create campaign summary

**Key Functions Needed**:
- `execute(config_path::String)::ReconstructionSummary`
- `execute_reconstruction_job(job, target_ts, source_ts, config)::ReconstructionJobResult`
- `apply_speed_reconstruction(target_ts, source_ts, speed_model, preserve_existing)`
- `apply_direction_reconstruction(target_ts, source_ts, direction_model, preserve_existing)`
- `validate_reconstructed_values(ts, metrics)::Bool`

**Dependencies Available**:
- ✅ CrossMastSpeedModel and CrossMastDirectionModel types
- ✅ `reconstruct()` functions in CrossMastSpeedCorrelation.jl and CrossMastDirectionAnalysis.jl
- ✅ TimeSeriesData loading/saving infrastructure
- ✅ Configuration types and serialization

### Phase 4: Quality Assessment Integration ❌ **FUTURE**
**Location: ReconstructCross/ directory**

#### Optional Enhancement: `ReconstructCross/QualityAssessment.jl`
- Detailed quality reports generation
- Visualization plots for reconstruction validation
- Quality scoring and recommendations

### Implementation Priority for Next Session:
1. **Immediate**: Implement `ProcessReconstructCrossCommand.jl`
2. **Secondary**: Add CLI integration for process command
3. **Testing**: Validate complete workflow with example project
4. **Optional**: Quality assessment and reporting enhancements