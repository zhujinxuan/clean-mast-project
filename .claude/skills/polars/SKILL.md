---
name: polars
description: Polars expression-first data processing. Use for DataFrame transformations where performance matters. Emphasizes building expressions before application, avoiding eager Series extraction.
---

# Polars Expression-First Data Processing

## The Golden Rule

**Build expressions first, then apply them once.**

```python
# ❌ WRONG: Eager extraction and Python operations
speed = df["wind_speed"]  # Extracts Series
result = speed * 2  # Python operation
df = df.with_columns(result.alias("new"))  # Put back

# ✅ RIGHT: Expression-first
expr = pl.col("wind_speed") * 2  # Build expression
df = df.with_columns(expr.alias("new"))  # Apply once
```

## Quick Patterns

### 1. Column Operations
```python
df.with_columns(
    doubled=pl.col("value") * 2,
    logged=pl.col("value").log()
)
```

### 2. Filtering
```python
df.filter(
    pl.col("age") > 25,
    pl.col("city").is_in(["NY", "LA"])
)
```

### 3. Aggregations
```python
df.group_by("category").agg(
    pl.col("value").mean().alias("avg"),
    pl.col("value").sum().alias("total")
)
```

### 4. Conditionals
```python
pl.when(pl.col("score") >= 90).then("A")
  .when(pl.col("score") >= 80).then("B")
  .otherwise("C")
```

### 5. Window Functions
```python
df.with_columns(
    group_mean=pl.col("value").mean().over("category"),
    rank=pl.col("value").rank().over("category")
)
```

### 6. Dynamic Columns
```python
# Sum multiple columns safely
cols = ["a", "b", "c"]
expr = sum([pl.col(c) for c in cols], pl.lit(0.0))
df.with_columns(total=expr)
```

## Schema Validation with dataframely

Use **dataframely** for schema validation at boundaries:

### When Loading External Data (with Sensor Metadata)

For wind data with dynamic column names from SensorColumn metadata, create schema dynamically:

```python
import dataframely as dy
import hashlib
from cleanmast.models.sensor import SensorColumn

def _hash_sensors(sensors: list[SensorColumn]) -> str:
    """Generate 6-char hash from sensor metadata for unique schema naming."""
    # Create deterministic string from sorted sensor columns
    sensor_str = ",".join(sorted(s.column_name for s in sensors))
    return hashlib.sha256(sensor_str.encode()).hexdigest()[:6]

def create_wind_schema(
    sensors: list[SensorColumn],
    mast_name: str | None = None
) -> type[dy.Schema]:
    """Dynamically create dataframely Schema from sensor metadata.
    
    - timestamp: Required, non-nullable
    - Sensor columns: All nullable Float64 (data may be missing)
    - Schema name includes mast_name or sensor hash for uniqueness
    """
    fields = {"timestamp": dy.Datetime(nullable=False)}
    
    for sensor in sensors:
        fields[sensor.column_name] = dy.Float64(nullable=True)
    
    # Unique name: mast name or hash of sensors
    if mast_name:
        schema_name = f"WindSchema_{mast_name}"
    else:
        token = _hash_sensors(sensors)
        schema_name = f"WindSchema_{token}"
    
    return type(schema_name, (dy.Schema,), fields)

# Implementation location
# See: packages/cleanmast/src/cleanmast/io/timeseries_validation.py
# And: packages/cleanmast/src/cleanmast/io/timeseries_io.py

from pathlib import Path

def load_and_validate(
    df: pl.DataFrame,
    sensors: list[SensorColumn],
    data_path: Path  # Use pathlib.Path for mast name extraction
) -> pl.DataFrame:
    # Extract mast name from filename (e.g., "TGL1" from "TGL1.parquet")
    mast_name = data_path.stem
    WindSchema = create_wind_schema(sensors, mast_name)
    return WindSchema.validate(df, cast=True)  # Raises if invalid

# Multi-mast example with pathlib.Path
for mast in masts:
    data_path = Path(mast.data_path)
    df = pl.read_parquet(data_path)
    sensors = extract_sensors_from_metadata(data_path)
    # mast_name auto-extracted from data_path.stem
    df = load_and_validate(df, sensors, data_path)
```

**Note:** This validation is implemented in `timeseries_validation.py` and integrated into `timeseries_io.py` (not in `fill_heights/recommend/validation.py` which is for config validation).

### When Creating DataFrames (Fixed Schema)

Define schema for outputs that must match a contract:

```python
class TIMatrixSchema(dy.Schema):
    """TI matrix must have v_max + 16 direction sectors."""
    v_max = dy.Float64(nullable=False)
    N = dy.Float64(nullable=False, min=0, max=1.0)
    NNE = dy.Float64(nullable=False, min=0, max=1.0)
    # ... all 16 sectors

# Return validated DataFrame
def calculate_ti_matrix(...) -> dy.DataFrame[TIMatrixSchema]:
    result = pl.DataFrame({...})
    return TIMatrixSchema.validate(result, cast=True)
```

### Schema Definition Rules

- **External input**: Always validate, use `cast=True` for flexibility
- **Internal output**: Validate at function boundaries
- **Nullable fields**: Explicitly mark `nullable=True/False`
- **Value ranges**: Add `min=`/`max=` for physical constraints

## Anti-Patterns Checklist

Before committing code:
- [ ] No `iter_rows()` in loops — use expressions
- [ ] No `df["col"]` in transformations — use `pl.col("col")`
- [ ] No building expressions with `+=` in loops — use `sum([...])`
- [ ] No `to_numpy()` unless truly necessary
- [ ] Multiple `with_columns()` merged into one call

## Pattern Reference

| Task | Pattern |
|------|---------|
| Add calculated column | `with_columns(expr.alias("new"))` |
| Multiple columns | `with_columns([expr1.alias("a"), ...])` |
| Conditional logic | `pl.when(cond).then(a).otherwise(b)` |
| Group statistics | `group_by().agg([...])` |
| Row-over-row within group | `.over(partition)` |
| Multi-column operations | `sum(pl.col(c) for c in cols)` |
| Lazy evaluation | `scan_csv().filter().select().collect()` |

## References

Load these for detailed guidance when needed:
- `references/operations.md` — Complete operation patterns
- `references/best_practices.md` — Performance optimization & pitfalls
