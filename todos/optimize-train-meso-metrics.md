# Optimize train-meso Metrics Computation

## Purpose

Eliminate redundant data preparation during metrics computation to improve performance of the `train-reconstruct-meso` command.

## Problem Statement

Currently, the `train-reconstruct-meso` command calls `prepare_training_data()` **twice** for each mast-meso pair:

1. **During model training** (parallel execution):
   - `train_mast_meso_pair()` → `train_meso_windspeed_sectorized()` / `train_meso_winddirection_directionoffset()` → `prepare_training_data()`
   - Performs: interval detection, regularization, and meso data interpolation

2. **During metrics computation** (sequential execution):
   - `compute_train_meso_metrics()` → `prepare_training_data()`
   - Repeats the exact same expensive operations to compute correlation

### Why This is Expensive

The `prepare_training_data()` function performs computationally intensive operations:
- **Interval detection**: Analyzes entire mast time series to detect representative intervals
- **Regularization**: May fill gaps in mast data using interpolation
- **Meso interpolation**: Resamples meso data to match mast timestamps (expensive for large datasets)

For large datasets (e.g., multiple years of 10-minute data), these operations can take **seconds to minutes per pair**. With parallel training, the sequential metrics computation step becomes a significant bottleneck.

### Current Implementation Flow

```
Load Data
    ↓
Parallel Training (fast)
    ├─ Pair 1: prepare_training_data() + train models
    ├─ Pair 2: prepare_training_data() + train models
    └─ Pair N: prepare_training_data() + train models
    ↓
Sequential Metrics (slow) ← BOTTLENECK
    ├─ Pair 1: prepare_training_data() + compute correlation
    ├─ Pair 2: prepare_training_data() + compute correlation
    └─ Pair N: prepare_training_data() + compute correlation
    ↓
Save Results
```

## Proposed Solution

**Compute correlation metrics during training** to eliminate the separate metrics computation step entirely.

### Modified Implementation Flow

```
Load Data
    ↓
Parallel Training with Metrics (fast)
    ├─ Pair 1: prepare_training_data() + train models + compute correlation
    ├─ Pair 2: prepare_training_data() + train models + compute correlation
    └─ Pair N: prepare_training_data() + train models + compute correlation
    ↓
Aggregate and Save Results (trivial)
```

## Implementation Details

### 1. Modify `train_mast_meso_pair()` Function

**Current signature:**
```julia
function train_mast_meso_pair(mast_name::String, meso_name::String,
                              models::Vector{TrainMesoModel},
                              mast_ts::TimeSeriesData, meso_ts::TimeSeriesData,
                              project_dir::String)
    # Returns: Vector{Tuple{TrainMesoModel, AbstractMastReferenceModel}}
end
```

**New signature:**
```julia
function train_mast_meso_pair(mast_name::String, meso_name::String,
                              models::Vector{TrainMesoModel},
                              mast_ts::TimeSeriesData, meso_ts::TimeSeriesData,
                              project_dir::String)
    # Returns: Tuple{
    #   Vector{Tuple{TrainMesoModel, AbstractMastReferenceModel}},
    #   Vector{TrainMesoSpeedMetrics}
    # }
end
```

### 2. Add Correlation Computation During Training

Inside `train_mast_meso_pair()`, after training models:

```julia
function train_mast_meso_pair(...)
    # Existing: prepare training data
    mast_aligned, meso_aligned = prepare_training_data(mast_ts, meso_ts)

    # Existing: train models
    for model_config in models
        # ... training code ...
    end

    # NEW: compute correlation metrics using already-aligned data
    model_metrics = compute_metrics_for_pair(
        mast_aligned, meso_aligned,
        models, mast_name, meso_name
    )

    return (trained_models, model_metrics)
end
```

### 3. Extract Metrics Computation Helper

Create a new helper function that uses already-aligned data:

```julia
function compute_metrics_for_pair(
    mast_aligned::TimeSeriesData,
    meso_aligned::TimeSeriesData,
    models::Vector{TrainMesoModel},
    mast_name::String,
    meso_name::String
)::Vector{TrainMesoSpeedMetrics}
    # Select highest-height avg WindSpeed sensors
    mast_ws = filter(s -> s.statType == "avg" && s.sensorType == "WindSpeed"
                        && s.height <= 160.0, mast_aligned.sensors)
    meso_ws = filter(s -> s.statType == "avg" && s.sensorType == "WindSpeed",
                        meso_aligned.sensors)

    isempty(mast_ws) && error("No wind speed sensors in mast $(mast_name)")
    isempty(meso_ws) && error("No wind speed sensors in meso $(meso_name)")

    mast_high = argmax(s -> s.height, mast_ws)
    meso_high = argmax(s -> s.height, meso_ws)

    mast_vec = mast_aligned.df[!, mast_high.columnName]
    meso_vec = meso_aligned.df[!, meso_high.columnName]

    mask = .!(ismissing.(mast_vec) .| ismissing.(meso_vec))
    count(mask) == 0 && error("No overlapping non-missing windspeed samples")

    m = collect(skipmissing(mast_vec[mask]))
    e = collect(skipmissing(meso_vec[mask]))
    corr = cor(m, e)

    # Record metrics only if 1-sector method is present
    has_1sector = any(model -> model.method == "1-sector", models)
    model_metrics = TrainMesoSpeedMetrics[]
    if has_1sector
        push!(model_metrics, TrainMesoSpeedMetrics("1-sector", corr))
    end

    return model_metrics
end
```

### 4. Update Main Execute Function

**Replace this section** in `CommandTrainMeso.jl`:

```julia
# OLD: Collect only trained models
@threads for idx in eachindex(pair_list)
    # ...
    train_mast_meso_pair(...)
    # ...
end

# OLD: Separate sequential metrics computation
@info "Computing training metrics"
results = compute_train_meso_metrics(config, mast_data, meso_data, model_groups)
```

**With:**

```julia
# NEW: Collect both models and metrics in parallel
pair_metrics = Vector{Tuple{
    Tuple{String, String},  # (mast_name, meso_name)
    Vector{TrainMesoSpeedMetrics}
}}(undef, length(pair_list))

@threads for idx in eachindex(pair_list)
    # ...
    trained_models, metrics = train_mast_meso_pair(...)
    pair_metrics[idx] = ((mast_name, meso_name), metrics)
    # ...
end

# NEW: Aggregate metrics (trivial operation)
@info "Aggregating training metrics"
results = aggregate_train_meso_metrics(config, pair_metrics)
```

### 5. Create Lightweight Aggregation Function

```julia
function aggregate_train_meso_metrics(
    config::TrainMesoConfiguration,
    pair_metrics::Vector{Tuple{Tuple{String, String}, Vector{TrainMesoSpeedMetrics}}}
)::TrainMesoResults
    pairs = TrainMesoPairResult[]

    # Entities for output
    mast_entities = Dict(m.name => TrainMesoEntity(m.name, m.input)
                        for m in config.masts)
    meso_entities = Dict(m.name => TrainMesoEntity(m.name, m.input)
                        for m in config.mesos)

    # Simply collect pre-computed metrics
    for ((mast_name, meso_name), metrics) in pair_metrics
        push!(pairs, TrainMesoPairResult(
            mast_entities[mast_name],
            meso_entities[meso_name],
            metrics
        ))
    end

    return TrainMesoResults(pairs)
end
```

### 6. Remove Old Function

Delete the `compute_train_meso_metrics()` function entirely, as it's no longer needed.

## Benefits

### Performance Improvements

1. **Eliminate redundant work**: `prepare_training_data()` called only once per pair
2. **Remove sequential bottleneck**: Metrics computed in parallel with training
3. **Reduced memory pressure**: No need to reload/reprocess data after training

### Expected Speedup

For N mast-meso pairs:
- **Before**: Training time + N × (interval detection + regularization + interpolation)
- **After**: Training time + trivial aggregation

For typical projects with 5-10 pairs and large datasets:
- **Estimated improvement**: 30-50% reduction in overall runtime

### Code Quality

1. **Cleaner architecture**: Single responsibility - training includes all computations
2. **Better data locality**: Metrics computed immediately after training with hot cache
3. **Reduced code duplication**: Same aligned data used for both training and metrics

## Implementation Checklist

- [ ] Extract correlation computation into `compute_metrics_for_pair()` helper
- [ ] Modify `train_mast_meso_pair()` to return both models and metrics
- [ ] Update return type handling in parallel training loop
- [ ] Create lightweight `aggregate_train_meso_metrics()` function
- [ ] Remove old `compute_train_meso_metrics()` function
- [ ] Update tests to verify metrics are still computed correctly
- [ ] Add timing logs to measure actual performance improvement
- [ ] Update documentation to reflect new flow

## Testing Strategy

1. **Unit tests**: Verify `compute_metrics_for_pair()` produces same results as old code
2. **Integration tests**: Ensure `train-meso-results.toml` output format unchanged
3. **Performance tests**: Compare before/after runtime on real project data
4. **Regression tests**: Verify correlation values match between old and new implementation

## Backward Compatibility

This is an **internal optimization** with no external API changes:
- Configuration files remain unchanged
- Output file format (`train-meso-results.toml`) remains unchanged
- CLI interface remains unchanged
- Only internal function signatures modified

## Future Enhancements

After implementing this optimization, consider:

1. **Extend metrics**: Add more quality metrics (RMSE, MAE, bias) computed during training
2. **Model-specific metrics**: Different metrics for 16-sector vs 1-sector vs direction models
3. **Height-specific metrics**: Correlation at multiple height levels, not just highest
4. **Time-series metrics**: Seasonal correlation, diurnal patterns, etc.

All future metrics should follow the same pattern: compute during training to avoid redundant work.

## References

- Current implementation: `src/TrainMeso/CommandTrainMeso.jl`
- Core training functions: `src/TrainMeso/Core.jl`
- Results types: `src/Types/TrainMesoResultsTypes.jl`
- Related optimization: Parallel reconstruction in `src/ReconstructCross/ProcessReconstructCrossCommand.jl`
