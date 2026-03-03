---
id: data-002-functional-programming
name: functional-programming
description: Functional programming patterns for data processing with pragmatic allowance for imperative patterns when building collections
status: enforced
tags: [julia, functional, data-processing, filter, map, broadcast, loops, style]
applies_when:
  - writing julia code
  - data transformations
  - building collections
  - iterating over data
---

# ADR data-002: Functional Programming Approach

## Status

Enforced

## Constraint (MUST)

1. **AVOID imperative loops with `push!` for simple data transformations** - use `filter()`, `map()`, or broadcasting instead
2. **MUST use functional style for data filtering and mapping** - prefer `filter()` and `map()` over `for` loops with conditionals
3. **MUST use DataFrame joins** (`leftjoin`, `innerjoin`) instead of manual merging with loops
4. **MUST use broadcasting** (`.|>`) for element-wise operations on vectors
5. **MAY use `push!` when building result collections iteratively** - pragmatically acceptable for accumulating complex results
6. **MAY use `for` loops when performance is critical** or when functional style becomes convoluted

## Rationale (WHY)

- **Functional style** produces cleaner, more declarative code that is easier to reason about and test
- **DataFrame joins** leverage optimized library implementations instead of manual O(n²) loops
- **Broadcasting** is idiomatic Julia and performs better than explicit loops
- **`push!` pragmatism** acknowledges that building collections incrementally is sometimes the clearest approach

## Pattern (HOW)

### Filter and Map for Data Processing

```julia
# ✅ CORRECT: Functional style with filter
validSensors = filter(s -> s.sensorType == "WindSpeed", sensors)

# ✅ CORRECT: Functional style with map
heights = map(s -> s.height, sensors)

# ✅ CORRECT: List comprehension (functional)
heights = [s.height for s in sensors if s.sensorType == "WindSpeed"]

# ✅ CORRECT: Method chaining with pipe
windSpeeds = sensors |>
    sensors -> filter(s -> s.sensorType == "WindSpeed", sensors) |>
    sensors -> map(s -> s.height, sensors)
```

### Broadcasting for Vector Operations

```julia
# ✅ CORRECT: Broadcasting with dot syntax
windPower = windSpeeds .|> speed -> 0.5 * 1.225 * speed^3

# ✅ CORRECT: Broadcasting arithmetic
adjustedSpeeds = windSpeeds .* 1.1 .+ 0.5
```

### DataFrame Joins Instead of Manual Merging

```julia
# ✅ CORRECT: Using join operations
combinedData = leftjoin(mastData, mesoData; on = :timestamp)

# ✅ CORRECT: Join with multiple columns
result = innerjoin(df1, df2; on = [:timestamp, :sensorId])
```

### Pragmatic push! for Building Collections

```julia
# ✅ ACCEPTABLE: Building results incrementally with push!
results = Vector{ViolationData}()
for row in eachrow(df)
    if condition(row)
        push!(results, createViolation(row))
    end
end

# ✅ ACCEPTABLE: Complex accumulation that is clearer with push!
violations = ViolationData[]
for sensor in sensors
    v = checkSensor(df, sensor)
    if !isempty(v)
        push!(violations, v...)
    end
end
```

## Anti-Pattern (AVOID)

```julia
# ❌ WRONG: Simple filter done imperatively
results = Float64[]
for row in eachrow(df)
    if row.windSpeed > threshold
        push!(results, row.windSpeed)
    end
end

# ✅ CORRECT:
results = filter(row -> row.windSpeed > threshold, df).windSpeed

# ❌ WRONG: Simple map done imperatively
heights = Float64[]
for sensor in sensors
    if sensor.sensorType == "WindSpeed"
        push!(heights, sensor.height)
    end
end

# ✅ CORRECT:
heights = [s.height for s in sensors if s.sensorType == "WindSpeed"]

# ❌ WRONG: Manual merging with loops instead of joins
combined = DataFrame()
for row1 in eachrow(df1)
    for row2 in eachrow(df2)
        if row1.timestamp == row2.timestamp
            # merge manually
        end
    end
end

# ✅ CORRECT:
combined = leftjoin(df1, df2; on = :timestamp)
```

## Phase Links

| Phase | File | Purpose |
|-------|------|---------|
| **on-plan** | [phases/data-002-functional-programming/on-plan.md](./phases/data-002-functional-programming/on-plan.md) | Design guidance for data transformations |
| **review-plan** | [phases/data-002-functional-programming/review-plan.md](./phases/data-002-functional-programming/review-plan.md) | Review checklist for data processing design |
| **code** | [phases/data-002-functional-programming/code.md](./phases/data-002-functional-programming/code.md) | Implementation patterns for data processing |
| **review-implementation** | [phases/data-002-functional-programming/review-implementation.md](./phases/data-002-functional-programming/review-implementation.md) | Code review for functional style compliance |

## References

- [Julia Documentation - Functional Programming](https://docs.julialang.org/en/v1/manual/functions/)
- [DataFrames.jl Join Operations](https://dataframes.juliadata.org/stable/man/joins/)
- Code verification: 219 `filter()` usages, 146 `map()` usages, 249 `push!` usages across 67 files
- AGENTS.md functional programming section
