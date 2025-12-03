# Train-Meso Performance Investigation

## Investigation Summary

This document identifies DataFrame performance bottlenecks found in the `train-meso` functionality based on common DataFrames.jl anti-patterns.

## Performance Issues Identified

### High Priority Issues

#### 1. Double Iteration Over Clusters Dictionary
**File**: `src/ReconstructMeso/RecommendReconstructMesoCommand.jl:381-421`

**Problem**: The code iterates over the same `clusters` dictionary twice:
- First loop (381-389): Calculates `individual_periods` for single-mast clusters
- Second loop (394-421): Re-iterates to assign periods to all masts

**Impact**: HIGH - Redundant iteration, particularly costly if there are many clusters

**Optimization**: Combine both loops into a single pass

---

#### 2. Loop with push! for Building Results Vector
**File**: `src/TrainMeso/CommandTrainMeso.jl:95-131` (compute_train_meso_metrics)

**Problem**:
```julia
pairs = TrainMesoPairResult[]
for ((mast_name, meso_name), models) in model_groups
    # ... processing ...
    push!(pairs, TrainMesoPairResult(...))
end
```

**Impact**: MEDIUM - Vector reallocation overhead with each push!

**Optimization**: Use functional pattern with `map`:
```julia
pairs = map(collect(model_groups)) do ((mast_name, meso_name), models)
    # ... processing ...
    TrainMesoPairResult(...)
end
```

---

#### 3. Loop with push! for Building Sensor Pairs
**File**: `src/WindSpeedModels/SectorizedRegressionTraining.jl:30-68`

**Problem**:
```julia
speed_pairs = Vector{SpeedPair}()
for mast_sensor in mast_speed_sensors
    # ... validation and processing ...
    push!(speed_pairs, SpeedPair(...))
end
```

**Impact**: MEDIUM - Vector reallocation, though mitigated by early exits

**Optimization**: Use `map` + `filter` pattern to handle conditional logic:
```julia
speed_pairs = mast_speed_sensors |>
    sensors -> map(sensors) do sensor
        # validation returns nothing on failure
        # processing returns SpeedPair on success
    end |>
    pairs -> filter(!isnothing, pairs)
```

---

### Medium Priority Issues

#### 4. Unnecessary collect() Allocations
**File**: `src/TrainMeso/CommandTrainMeso.jl:118-119`

**Problem**:
```julia
m = collect(skipmissing(mast_vec[mask]))
e = collect(skipmissing(meso_vec[mask]))
```

**Impact**: MEDIUM - Extra memory allocation when `cor()` should work with iterators

**Optimization**: Check if `cor()` accepts iterators directly, or use views:
```julia
# If cor() supports iterators:
corr = cor(skipmissing(mast_vec[mask]), skipmissing(meso_vec[mask]))

# Otherwise, pre-allocate or use views where possible
```

---

#### 5. Two-Pass Data Filtering
**File**: `src/WindSpeedModels/SectorizedRegressionTraining.jl:103-105`

**Problem**:
```julia
dropmissing!(df)
df = filter(row -> row.mast_speed > 0 && row.meso_speed > 0, df)
```

**Impact**: LOW-MEDIUM - Two passes through data when one would suffice

**Optimization**: Combine into single filter operation:
```julia
df = filter(row -> !any(ismissing, row) && row.mast_speed > 0 && row.meso_speed > 0, df)
```

---

#### 6. DataFrame Column Assignment in Loop
**File**: `src/WindSpeedModels/SectorizedRegressionTraining.jl:120`

**Problem**:
```julia
data[:, :sector_name] = map(data.meso_dir) do dir
    # ... sector assignment ...
end
```

**Impact**: LOW - In-place modification is acceptable here, though the pattern is used

**Note**: This is actually fine for single column assignment. Only problematic if done repeatedly in a loop.

---

## Optimization Strategies Summary

### Strategy 1: Eliminate Double Cluster Iteration
Combine the two loops in `ReconstructMeso/RecommendReconstructMesoCommand.jl:381-421` into a single pass.

**Pattern**:
```julia
# Instead of:
# Loop 1: Calculate individual_periods for single-mast
# Loop 2: Assign periods using cached or fresh calculations

# Do:
for (cluster_id, cluster_masts) in clusters
    if length(cluster_masts) == 1
        # Calculate and assign in one step
    else
        # Calculate and assign in one step
    end
end
```

---

### Strategy 2: Replace push! Loops with Functional Patterns
Use `map` + `filter` patterns instead of manual loops with `push!`.

**Benefits**:
- Pre-allocated result vectors (map knows the size)
- More idiomatic Julia
- Easier to parallelize later if needed

**Pattern**:
```julia
# Instead of:
results = Type[]
for item in items
    if valid(item)
        push!(results, process(item))
    end
end

# Use:
results = items |>
    xs -> map(process, xs) |>
    xs -> filter(valid, xs)

# Or for more complex cases:
results = map(items) do item
    valid(item) ? process(item) : nothing
end |> xs -> filter(!isnothing, xs)
```

---

### Strategy 3: Combine Filter Operations
Merge multiple filter passes into single combined conditions.

**Benefits**:
- Single pass through data
- Reduced intermediate allocations
- Better cache locality

**Pattern**:
```julia
# Instead of:
dropmissing!(df)
df = filter(row -> condition1(row), df)
df = filter(row -> condition2(row), df)

# Use:
df = filter(row -> !any(ismissing, row) && condition1(row) && condition2(row), df)
```

---

### Strategy 4: Remove Unnecessary Allocations
Pass iterators directly to functions that support them instead of collecting.

**Investigation Needed**:
- Check if `Statistics.cor()` can work with iterator inputs
- Consider using views instead of copies where appropriate

---

## Files Requiring Changes

1. **`src/ReconstructMeso/RecommendReconstructMesoCommand.jl`** - HIGH priority
   - Lines 381-421: Eliminate double cluster iteration

2. **`src/TrainMeso/CommandTrainMeso.jl`** - MEDIUM priority
   - Lines 95-131: Replace push! loop in `compute_train_meso_metrics`
   - Lines 118-119: Remove unnecessary collect() if possible

3. **`src/WindSpeedModels/SectorizedRegressionTraining.jl`** - MEDIUM priority
   - Lines 30-68: Replace push! loop with functional pattern
   - Lines 103-105: Combine two-pass filtering

---

## Implementation Notes

### Testing Strategy
1. Run existing tests to establish baseline
2. Refactor one function at a time
3. Verify tests still pass after each change
4. Consider adding performance benchmarks

### Benchmarking
- Use `@time` or `BenchmarkTools.jl` to measure before/after
- Focus on real-world project datasets
- Measure both time and memory allocations

### Risk Assessment
- **Low Risk**: Combining filter operations (pure refactor)
- **Medium Risk**: Replacing push! loops (logic must be preserved)
- **High Risk**: Double iteration removal (complex logic interaction)

---

## Additional Considerations

### Split-Apply-Combine Patterns
The code already uses `groupby` appropriately in `SectorizedRegressionTraining.jl:129`. This is good practice and should be maintained.

### When push! is Acceptable
- Small, bounded iterations (<100 items)
- When early exits are frequent and complex
- Prototyping code

For production code with potentially large datasets, prefer functional patterns.

---

## References

- DataFrames.jl documentation: https://dataframes.juliadata.org/
- Julia Performance Tips: https://docs.julialang.org/en/v1/manual/performance-tips/
- Avoid growing arrays with push!: Use comprehensions or map when size is known
