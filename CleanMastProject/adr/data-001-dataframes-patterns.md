---
id: data-001-dataframes-patterns
name: dataframes-patterns
description: DataFrames.jl patterns for wind energy data processing. Column access MUST use Symbols, not strings. Operations use filter(), transform(), select(), and join() with functional patterns.
status: enforced
tags: [julia, dataframes, symbols, data-processing, wind-energy]
applies_when:
  - data processing
  - DataFrames operations
  - column access
  - data transformation
---

# ADR-001: DataFrames.jl Patterns

## Status
**Enforced**

## Constraint (MUST)

1. **Column access MUST use Symbols, NOT strings**
2. **filter() MUST use row -> predicate(row.column) pattern**
3. **transform() MUST use column references as Symbols**
4. **join operations MUST use on = :column (Symbol)**
5. **Missing value checks MUST use ismissing()**
6. **Dynamic column names MUST convert to Symbol**

## Rationale (WHY)

- **Symbols for columns**: Julia DataFrames require Symbol types for column operations. Using strings causes runtime errors.
- **filter() pattern**: The row -> predicate pattern is the standard DataFrames.jl idiom for filtering rows based on column conditions.
- **transform() pattern**: Enables efficient column transformations while maintaining type safety through Symbol references.
- **join operations**: Consistent use of Symbols in on clauses prevents join failures.
- **ismissing()**: The correct way to check for missing values in Julia, distinct from nothing or NaN.

## Pattern (HOW)

### Column Access with Symbols

```julia
# ✅ CORRECT: Using Symbols for column access
df[:, :wind_speed]
select(df, :timestamp, :wind_speed)
df[:, [:wind_speed, :wind_direction]]

# ✅ CORRECT: Using sensor.columnName (Symbol field)
wind_speed_data = df[:, wind_speed_sensor.columnName]
```

### filter() Usage

```julia
# ✅ CORRECT: Filter rows based on conditions
validRows = filter(row -> !ismissing(row.diff) && !ismissing(row.expectedRange), diffResult)

# ✅ CORRECT: Simple filter with single condition
clean_data = filter(row -> row.wind_speed >= 0, df)

# ✅ CORRECT: Multiple conditions
valid_data = filter(row -> !ismissing(row.wind_speed) && row.wind_speed < 50, df)
```

### transform() Usage

```julia
# ✅ CORRECT: Transform with ByRow
# From ProcessData.jl
df = transform(df, [:speed, :direction] => ByRow(compute_u_v) => [:u, :v])

# ✅ CORRECT: Creating new columns
# From ProcessLayerDiff.jl
df = transform(df, [:valueLower, :valueUpper] => ByRow((l, u) -> abs(l - u)) => :diff)

# ✅ CORRECT: Multiple transformations
df = transform(df,
    :wind_speed => (x -> x .* 2) => :wind_speed_doubled,
    :wind_direction => ByRow(normalize_direction) => :direction_normalized
)
```

### leftjoin() Usage

```julia
# ✅ CORRECT: Join with on as Symbol
# From WindRose.jl
df = leftjoin(df, sectorDF; on = :direction_bin)

# ✅ CORRECT: Multiple join columns
df = leftjoin(df, other_df; on = [:timestamp, :height])
```

### select() Usage

```julia
# ✅ CORRECT: Select specific columns
select(df, :timestamp, :wind_speed, :wind_direction)

# ✅ CORRECT: Select and rename
select(df, :timestamp, :wind_speed => :ws)

# ✅ CORRECT: Not selector (exclude columns)
select(df, Not(:temporary_column))
```

### ismissing() Checks

```julia
# ✅ CORRECT: Check for missing values
if ismissing(row.wind_speed)
    # handle missing
end

# ✅ CORRECT: Filter out missing
valid_data = filter(row -> !ismissing(row.wind_speed), df)

# ✅ CORRECT: Multiple column missing check
valid_rows = filter(row -> !ismissing(row.speed) && !ismissing(row.direction), df)
```

### String to Symbol Conversion

```julia
# ✅ CORRECT: Dynamic column access
col_name = "wind_speed_80m"
df[:, Symbol(col_name)]

# ✅ CORRECT: Building column names dynamically
heights = [10, 40, 80]
cols = [Symbol("wind_speed_$(h)m") for h in heights]
select(df, :timestamp, cols...)
```

## Anti-Pattern (AVOID)

```julia
# ❌ WRONG: Using strings for column access (causes error)
select(df, "wind_speed", "wind_direction")  # NEVER!
df[:, "wind_speed"]  # NEVER!

# ❌ WRONG: Missing check with === nothing
if row.wind_speed === nothing  # NEVER - use ismissing()

# ❌ WRONG: Imperative loop building
results = DataFrame()
for row in eachrow(df)
    if row.wind_speed > threshold
        push!(results, row)  # NEVER - use filter()
    end
end

# ❌ WRONG: Using eval for dynamic columns
eval(Symbol(col_name))  # NEVER - use Symbol() directly
```

## Phase Links

This ADR uses **phase-based documentation**. Load the appropriate phase file for your role:

| Phase | File | When to Load |
|-------|------|--------------|
| **on-plan** | [`phases/data-001-dataframes-patterns/on-plan.md`](phases/data-001-dataframes-patterns/on-plan.md) | Designer: Data processing design |
| **review-plan** | [`phases/data-001-dataframes-patterns/review-plan.md`](phases/data-001-dataframes-patterns/review-plan.md) | Reviewer: Validating designs |
| **code** | [`phases/data-001-dataframes-patterns/code.md`](phases/data-001-dataframes-patterns/code.md) | Coder: Implementation |
| **review-implementation** | [`phases/data-001-dataframes-patterns/review-implementation.md`](phases/data-001-dataframes-patterns/review-implementation.md) | Reviewer: Code review |

### Quick Compliance Check

```bash
# Validate ADR-001 compliance - check for string column access (anti-pattern)
grep -rn 'df\[:, "' src/ || echo "OK: No string column access found"
grep -rn 'select(.*, "' src/ || echo "OK: No string select found"

# Validate Symbol usage
grep -rn 'df\[:, :' src/ | head -5 && echo "OK: Symbol column access found"
```

## References

- [ProcessRange.jl](../src/DataClean/ProcessRange.jl) - filter() usage
- [ProcessLayerDiff.jl](../src/DataClean/ProcessLayerDiff.jl) - transform() and filter() patterns
- [ProcessData.jl](../src/ReconstructSingleMast/ProcessData.jl) - transform() with ByRow
- [WindRose.jl](../src/AnalyzeTimeSeries/WindRose.jl) - leftjoin() usage
- DataFrames.jl documentation: https://dataframes.juliadata.org/stable/
