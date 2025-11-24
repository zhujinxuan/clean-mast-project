# Algorithm for Aligned Meso Reconstruction Periods

## Overview
Implement smart clustering of masts based on data overlap (>80% threshold), with each cluster sharing an optimized common period.

## Problem Statement
Currently, each mast in reconstruct-meso gets an independent optimal period. When multiple masts have highly overlapping data coverage, they should share the same reconstruction period for consistency.

## Algorithm Steps

### 1. Calculate Pairwise Overlap Coverage
- For each mast pair, compute individual optimal periods (using current logic)
- Calculate overlap time range intersection length (in days)
- Compute dual-criterion overlap metric:
  ```julia
  relative_overlap = intersection_days / min(period_i_days, period_j_days)
  absolute_overlap = intersection_days / threshold_period  # Default: 120 days
  overlap[i,j] = max(relative_overlap, absolute_overlap)
  ```
- **Interpretation**: Cluster if **either**:
  - The shorter period is well-covered (relative criterion), **OR**
  - The intersection is long enough for correlation training (absolute criterion)
- **Example** (threshold_period=120 days):
  - 12mo + 12mo with 4mo intersection: `max(4/12, 4/4) = 1.0` ✓ (absolute wins)
  - 1mo + 12mo with 1mo intersection: `max(1/1, 1/4) = 1.0` ✓ (relative wins)
- **Note**: The overlap matrix is symmetric since both metrics are symmetric

### 2. Hierarchical Clustering
- Convert overlap matrix to distance: `distance[i,j] = 1 - overlap[i,j]`
- Apply hierarchical clustering with complete linkage
- Cut dendrogram at threshold height: `h = 1 - cluster_threshold` (default: 0.2 for 80% overlap)
- **Algorithm**: Complete linkage ensures ALL pairs in a cluster exceed the threshold
- **Result**: groups of highly-overlapping masts + isolated single-mast clusters

### 3. Optimize Period Per Cluster
- **Single-mast clusters**: Use existing optimal period calculation
- **Multi-mast clusters**:
  1. **Calculate union time range**: Earliest start to latest end across all cluster masts
  2. **Determine target period length**:
     - `union_years = union_days / 365.0`
     - `target_years = max(1, round(Int, union_years))`  # Standard rounding, minimum 1 year
     - Examples: 1.4yr→1yr, 1.5yr→2yr, 2.3yr→2yr, 2.6yr→3yr
     - `target_days = target_years * 365`
  3. **Find optimal window**:
     - For each candidate N-year window starting at month beginning
     - Calculate combined coverage score across all cluster masts
     - Select window with highest score
  4. **Return period**: Month-aligned start and end dates

### 4. Assign Periods
- Each mast gets the optimal period of its cluster
- Masts in same cluster = identical time range

## Current Implementation Analysis

### Current Behavior (per-mast periods)
**File**: `src/ReconstructMeso/RecommendReconstructMesoCommand.jl:201-207`
- Each mast calls `calculate_optimal_measurement_period()` independently
- Always returns 1-year period (hardcoded 365 days)
- Each mast gets different optimal period

**Period Calculation**: `src/TimeSeriesProcessing/MeasurementPeriodCalculator.jl`
- `calculate_optimal_measurement_period()`: Main entry point
  - Takes single_ts, cross_ts, meso_ts as input
  - Calculates daily scores with weighted coverage (single=1.0, cross=0.5)
  - Uses `find_optimal_year_range()` to find best 365-day window
  - Returns month-aligned TimeRange
- **Hardcoded assumptions**:
  - 365-day window only (line 268: `for start_idx in 1:(length(score_vector) - 364)`)
  - Two-dataset weighting scheme (single vs cross)
  - Month boundary alignment

## Implementation Changes

### New File: `src/TimeSeriesProcessing/MastPeriodAlignment.jl`
Functions to implement:
- `calculate_pairwise_overlap()`: Overlap matrix computation using dual-criterion
- `cluster_masts_by_overlap()`: Hierarchical clustering with complete linkage
- `calculate_cluster_optimal_period()`: Multi-mast period optimization with flexible N-year windows
- Helper functions:
  - `determine_target_period_length(union_days::Int)::Int`: Round union period to N years
  - `calculate_union_time_range(mast_timeseries::Dict)::Tuple{Date, Date}`
  - `score_cluster_window(mast_timeseries::Dict, window_start::Date, window_end::Date)::Float64`

### Modified: `src/ReconstructMeso/RecommendReconstructMesoCommand.jl`

**Function signature updated** (lines 232-236):
- Add optional parameters:
  - `cluster_threshold::Float64 = 0.8`: Overlap threshold for clustering
  - `threshold_period::Int = 120`: Minimum intersection days for absolute criterion

**Refactor `execute()` function** (lines 250-254):
- **Current**: `map` each mast to call `create_mast_configuration()` independently
- **New approach**:
  1. Load all mast timeseries data first
  2. Calculate individual optimal periods for each mast (needed for overlap calculation)
  3. Build overlap matrix using `calculate_pairwise_overlap()`
  4. Cluster masts using `cluster_masts_by_overlap()`
  5. Calculate optimal period for each cluster using `calculate_cluster_optimal_period()`
  6. Map masts to configurations, passing cluster-assigned period

**Modify `create_mast_configuration()` function** (lines 178-218):
- Add optional parameter: `override_period::Union{Nothing, TimeRange} = nothing`
- If `override_period` is provided, use it instead of calling `calculate_optimal_measurement_period()`
- This allows cluster-based periods to be injected

### Modified: `src/TimeSeriesProcessing/MeasurementPeriodCalculator.jl`

**Refactor `find_optimal_year_range()` for flexible N-year periods** (lines 237-287):
- **Current**: Hardcoded 365-day window (line 267: `for start_idx in 1:(length(score_vector) - 364)`)
- **New**: Add parameter `target_days::Int` to support multi-year periods
- **Signature change**:
  ```julia
  function find_optimal_year_range(
      daily_scores::Vector{DailyScore},
      earliest_start_date::Date,
      latest_end_date::Date,
      target_days::Int = 365  # Default to 1 year for backward compatibility
  )::TimeRange
  ```
- **Update loop**: `for start_idx in 1:(length(score_vector) - (target_days - 1))`
- **Update end calculation**: `end_date = score_vector[best_start_idx + (target_days - 1)].date`
- **Update end_datetime**: Use `Day(target_days)` instead of `Year(1)`

**Update `calculate_optimal_measurement_period()` signature** (lines 316-349):
- Add optional parameter: `target_days::Int = 365`
- Pass `target_days` to `find_optimal_year_range()`
- **Note**: This change maintains backward compatibility for single-mast use case

### Modified: `src/CleanMastCli.jl`
- Update `recommend reconstruct-meso` command to expose clustering parameters
- **Usage**:
  ```bash
  julia bin/CleanMast.jl recommend reconstruct-meso ./projects/my-project
  julia bin/CleanMast.jl recommend reconstruct-meso ./projects/my-project --cluster-threshold 0.7 --threshold-period 90
  ```

### Tests: `test/TimeSeriesProcessing/test_mast_period_alignment.jl`
Test scenarios:
- **Pairwise overlap calculation**:
  - Dual-criterion overlap with various intersection lengths
  - Relative vs absolute criterion dominance
- **Hierarchical clustering**:
  - Complete linkage with different threshold values
  - Edge cases: isolated masts, fully connected, partial overlap
- **Period length determination**:
  - Union length = 1.4 years → target = 1 year
  - Union length = 1.5 years → target = 2 years
  - Union length = 2.6 years → target = 3 years
  - Union length < 1 year → error
- **Cluster period optimization**:
  - Multi-mast window scoring with different coverage patterns
  - Month alignment verification
  - Integration test for full workflow

## Implementation Workflow

### Step 1: Refactor MeasurementPeriodCalculator (Foundation)
- Make `find_optimal_year_range()` support N-year periods
- Add `target_days` parameter with default 365 for backward compatibility
- Update `calculate_optimal_measurement_period()` to accept `target_days`
- Write tests for multi-year period calculation

### Step 2: Implement MastPeriodAlignment (New Module)
- Create overlap matrix calculation with dual-criterion
- Implement hierarchical clustering with complete linkage
- Implement cluster period optimization using union range + rounding logic
- Write comprehensive tests

### Step 3: Integrate into RecommendReconstructMesoCommand
- Add clustering parameters to `execute()`
- Refactor to pre-calculate periods before mast configuration
- Add `override_period` parameter to `create_mast_configuration()`
- Update existing single-mast code path to maintain backward compatibility

### Step 4: Update CLI
- ✅ Already done: Added `--cluster-threshold` and `--threshold-period` parameters

## Design Decisions

**Overlap Metric**: Dual-criterion (relative + absolute coverage)
**Clustering Threshold**: `cluster_threshold = 0.8` (configurable parameter in recommend command)
**Absolute Period Threshold**: `threshold_period = 120 days` (configurable parameter in recommend command)
**Period Selection**: Optimized for group quality (find best N-year period for entire cluster)
**Period Length**: Flexible 1-N years based on union period with standard rounding (min 1 year)
**Clustering Method**: Hierarchical clustering with complete linkage
**Scope**: Only reconstruct-meso (not reconstruct-cross)

## Backward Compatibility
- Single-mast projects: No change in behavior
- Projects without high overlap: Each mast keeps independent period
- Existing configs: Still valid (can be regenerated with new logic)

## Data Dependencies

### Information Required for Clustering
For each mast, need to calculate individual optimal period first:
- **Input data**: Either reconstruct-cross or reconstruct-single output
- **Meso data**: For respecting meso boundaries
- **Single data**: For quality scoring
- **Output**: `TimeRange` (start, end) for each mast

### Information Required for Cluster Period Calculation
For each cluster of masts:
- **Input data sources**: Dict mapping mast_name → TimeSeriesSource
- **Loaded timeseries**: Dict mapping mast_name → TimeSeriesData
- **Meso data**: For boundary constraints (use from first mast's model)
- **Output**: Single `TimeRange` shared by all masts in cluster

### Key Constraint
- Must respect mesoscale data boundaries (max_allowed_end_time from meso)
- Period must start on month beginning (day = 1)
- Multi-mast scoring uses input reconstruction data (cross or single)

## Open Questions
- [ ] Should we log/report which masts were grouped together?
- [ ] What coverage scoring method for multi-mast windows? (average, minimum, weighted)
  - **Recommendation**: Average coverage for simplicity
- [ ] How to handle masts using different meso sources within a cluster?
  - **Current approach**: Use the meso from first mast's model, warn if different
