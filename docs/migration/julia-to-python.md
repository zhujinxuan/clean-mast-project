# Julia to Python Migration Guide

This document provides guidance for migrating CleanMast modules from Julia to Python.

## Philosophy

- **Incremental Migration**: Migrate one module at a time
- **Maintain Parity**: Python implementation should match Julia functionality
- **Leverage Ecosystem**: Use Python's strengths (pandas/polars, scipy, matplotlib)
- **Type Safety**: Use type hints and Pydantic for configuration validation

## Technology Mapping

### Data Processing

| Julia | Python | Notes |
|-------|--------|-------|
| DataFrames.jl | polars | **Use polars** for performance and type safety |
| CSV.jl | polars.read_csv() | Polars has better performance |
| DataFramesMeta.jl | polars expressions | More functional style |

**Note**: We have migrated from pandas to polars for better typing, performance, and functional programming style.

### Statistical Analysis

| Julia | Python | Notes |
|-------|--------|-------|
| GLM.jl | statsmodels / scikit-learn | For regression models |
| Distributions.jl | scipy.stats | Statistical distributions |
| StatsBase.jl | scipy.stats / numpy | Basic statistics |

### Visualization

| Julia | Python | Notes |
|-------|--------|-------|
| AlgebraOfGraphics.jl | seaborn / plotly | Grammar of graphics |
| CairoMakie.jl | matplotlib | Direct plotting |
| - | altair | Alternative declarative viz |

### CLI & Configuration

| Julia | Python | Notes |
|-------|--------|-------|
| Comonicon.jl | click | CLI framework |
| TOML.jl | tomli / tomllib | TOML parsing |
| Structs | Pydantic models | Type-safe configs |

## Code Style Differences

### Type Definitions

**Julia:**
```julia
struct SensorColumn
    sensorType::String
    height::Float64
    statType::String
end
```

**Python:**
```python
from pydantic import BaseModel

class SensorColumn(BaseModel):
    sensor_type: str
    height: float
    stat_type: str
```

### Data Transformations

**Julia (functional with pipe):**
```julia
result = data |>
    df -> filter(row -> !ismissing(row.wind_speed), df) |>
    df -> select(df, :timestamp, :wind_speed)
```

**Python (polars):**
```python
result = (
    data
    .filter(pl.col("wind_speed").is_not_null())
    .select(["timestamp", "wind_speed"])
)
```


### Configuration Loading

**Julia:**
```julia
config = TOML.parsefile(config_path)
ProcessCleanConfig(; config...)
```

**Python:**
```python
import tomli
from pathlib import Path

with Path(config_path).open("rb") as f:
    config_dict = tomli.load(f)
config = ProcessCleanConfig(**config_dict)
```

## Migration Checklist

When migrating a module:

- [ ] Read the Julia source code thoroughly
- [ ] Understand the algorithm and data flow
- [ ] Check existing Julia tests for expected behavior
- [ ] Create Python module structure matching Julia
- [ ] Implement core functionality
- [ ] Add type hints
- [ ] Port tests from Julia (use same test data)
- [ ] Add docstrings
- [ ] Verify numerical results match Julia output
- [ ] Update migration status

## Testing Strategy

### Test Data Compatibility

Use the same test fixtures as Julia tests:
- Keep test data in `packages/{package}/tests/fixtures/`
- Ensure numerical results match Julia implementation
- Use `pytest.approx()` for floating-point comparisons

### Test Structure

Mirror Julia test organization:
```
CleanMastProject/test/ParseSensors/
→ packages/cleanmast/tests/ParseSensors/
```

## Common Pitfalls

### 1. Symbol vs String in DataFrames

**Julia**: Uses `Symbol` for column names
```julia
df[:, :wind_speed]
```

**Python**: Uses strings
```python
df["wind_speed"]  # pandas
pl.col("wind_speed")  # polars
```

### 2. Missing Values

**Julia**: `missing` type
**Python**: `None`
**Polars**: Uses `null` for missing values across all types (more consistent than pandas)

```python
# Check for null values
df.filter(pl.col("wind_speed").is_not_null())

# Handle nulls
df.with_columns(pl.col("wind_speed").fill_null(0.0))
```

### 3. 1-based vs 0-based Indexing

Julia is 1-indexed, Python is 0-indexed. Be careful when translating array operations.

### 4. Mutation

Julia often uses `!` suffix for mutating functions.
Python: be explicit about whether functions mutate or return new objects.

## Module Priority Order

Recommended migration sequence:

1. ✅ **Preprocessing** (DONE - `preprocess-tools`)
2. ⏳ **Types** - Core type definitions
3. ⏳ **ParseSensors** - Sensor parsing and column mapping
4. ⏳ **DataClean** - Validation rules
5. ⏳ **ReconstructSingleMast** - Single-mast reconstruction
6. ⏳ **AnalyzeTimeSeries** - Time series analysis
7. ⏳ **ReconstructMeso** - Mesoscale integration
8. ⏳ **Reports** - Report generation
9. ⏳ **AnalyzeEN** - EN standard compliance
10. ⏳ **TowerShading** - Tower shadow correction

## Resources

- **Julia Docs**: [CleanMastProject/docs/](../../CleanMastProject/docs/)
- **Python Style Guide**: PEP 8
- **Type Hints**: PEP 484, 585
- **Pydantic**: https://docs.pydantic.dev/

## Questions?

Refer to the Julia implementation in `CleanMastProject/` for reference.
Consult `CLAUDE.md` for coding standards and domain-specific guidelines.
