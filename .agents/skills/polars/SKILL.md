---
name: polars
description: Polars expression-first data processing. Use for DataFrame transformations where performance matters. Emphasizes building expressions before application, avoiding eager Series extraction. Covers CleanMast wind-data patterns (u/v decomposition, sector binning, height filling) and dataframely schema validation.
license: MIT
compatibility:
  python: ">=3.12"
  polars: ">=1.25"
  dataframely: ">=2.13"
metadata:
  category: data
  tier: foundational
  tags: [polars, expressions, dataframes, wind-data, performance, dataframely]
  scope: project-level
---

## The Golden Rule

**Build expressions first, then apply them once.**

```python
# WRONG: Eager extraction and Python operations
speed = df["wind_speed"]       # Extracts Series
result = speed * 2             # Python operation
df = df.with_columns(result.alias("new"))

# RIGHT: Expression-first
expr = pl.col("wind_speed") * 2   # Build expression (lazy)
df = df.with_columns(expr.alias("new"))   # Apply once
```

Never extract a `pl.Series` into Python to do the work. Stay in expression space — it is lazy, parallelized, and composable.

## Quick Patterns

### 1. Column Operations
```python
df.with_columns(
    doubled=pl.col("value") * 2,
    logged=pl.col("value").log(),
    clipped=pl.col("value").clip(lower_bound=0.0, upper_bound=1.0)
)
```

### 2. Filtering
```python
df.filter(
    pl.col("height") > 60,
    pl.col("sensor_type").is_in(["WindSpeed", "WindDirection"])
)
```

### 3. Aggregations
```python
df.group_by("sector").agg(
    pl.col("ti").mean().alias("mean_ti"),
    pl.col("ti").std().alias("std_ti"),
    pl.len().alias("count")
)
```

### 4. Conditionals
```python
# Prefer pl.Enum for fixed category sets; pl.Categorical for open-ended
pl.when(pl.col("score") >= 90).then(pl.lit("A"))
  .when(pl.col("score") >= 80).then(pl.lit("B"))
  .otherwise(pl.lit("F"))
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
# Sum multiple columns safely — sum(list, start) handles empty lists
cols = ["a", "b", "c"]
expr = sum([pl.col(c) for c in cols], pl.lit(0.0))
df.with_columns(total=expr)
```

### 7. Horizontal Aggregations
```python
# Row-wise operations across columns
df.with_columns(
    max_val=pl.max_horizontal("col_a", "col_b", "col_c"),
    row_mean=pl.mean_horizontal("col_a", "col_b"),
    total=pl.sum_horizontal(pl.col("x"), pl.col("y"))
)
```

## Wind Data Patterns

### Wind-Vector Decomposition (u/v Components)

When combining multiple wind directions (e.g., height-filling via weighted interpolation), decompose to u/v components in expression space:

```python
# Convert wind direction to u/v components
rad = (pl.col("WindDirection_80m_avg [deg]") + deg_offset) % 360
u = rad.radians().sin() * weight
v = rad.radians().cos() * weight

# Sum across references with pl.sum_horizontal
u_expr = pl.sum_horizontal([
    ((pl.col(ref.column_name) + adj) % 360).radians().sin() * ref.weight
    for ref in references
])
v_expr = pl.sum_horizontal([
    ((pl.col(ref.column_name) + adj) % 360).radians().cos() * ref.weight
    for ref in references
])

# Reconstruct direction: arctan2 returns radians, convert to degrees
result = pl.arctan2(-u_expr, -v_expr).degrees() % 360
```

The key insight: **never average wind directions directly** — the mean of 10 and 350 is 360/2=180 (backwards!). Always decompose to u/v components first.

### Direction-Sector Binning

Map wind direction (0-360 degrees) to N-sector indices:

```python
SECTOR_WIDTH = 22.5   # 16 sectors (N, NNE, NE, ...)
NUM_SECTORS = 16

sector_expr = (
    ((pl.col("wind_direction") / SECTOR_WIDTH).floor() % NUM_SECTORS)
).cast(pl.Int32)

# Or as a reusable helper
def _direction_to_sector(wd_col: pl.Expr) -> pl.Expr:
    """Convert wind direction (0-360) to 16-sector index (0-15)."""
    return ((wd_col / 22.5).floor() % 16).cast(pl.Int32)
```

### SensorColumn-Driven Column Selection

In CleanMast, column names come from `SensorColumn` value objects — never hard-code column strings:

```python
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn

# SensorColumn carries: column_name, sensor_type, height, stat_type, sensor_direction, unit

# Build expressions from sensor objects
expr = pl.sum_horizontal([
    pl.col(ref.sensor.column_name)
    * ((target.height / ref.sensor.height) ** shear)
    * (ref.weight / total_weight)
    for ref in references
])

# Select columns via sensor metadata
ws_columns = [s.column_name for s in sensors if s.sensor_type == "WindSpeed"]
df.select(ws_columns)
```

### TI (Turbulence Intensity) Calculation

Standard pattern combining `pl.max_horizontal`, `clip`, and sector binning:

```python
ti_expr = (
    pl.col("ws_sd")
    / pl.max_horizontal(pl.col("ws_avg"), pl.lit(1.0))  # Avoid div-by-zero
).clip(upper_bound=1.0)  # Cap TI at 100%

sector_expr = ((pl.col("wd_avg") / 22.5).floor() % 16).cast(pl.Int32)

result = df.with_columns([
    ti_expr.alias("ti"),
    sector_expr.alias("sector"),
])
```

### Empty DataFrame Construction

When a function must return a DataFrame with a fixed schema even for no results:

```python
def empty_result() -> pl.DataFrame:
    """Return empty DataFrame matching the expected output schema."""
    return pl.DataFrame({
        "height":       pl.Series([], dtype=pl.Float64),
        "mean_ti":      pl.Series([], dtype=pl.Float64),
        "std_ti":       pl.Series([], dtype=pl.Float64),
        "count":        pl.Series([], dtype=pl.Int64),
        "iec_category": pl.Series([], dtype=pl.String),
    })
```

## Schema Validation with dataframely

### Rule: If the Shape Is Known, Guard It with dataframely

This is the dominant pattern in CleanMast. Every function that returns a DataFrame with a contract-bound shape should:

1. **Define a `dy.Schema` subclass** describing every column, its type, nullability, and physical value ranges.
2. **Annotate the return type** as `dy.DataFrame[MySchema]` (or `dy.LazyFrame[MySchema]`).
3. **Validate before returning**: `MySchema.validate(df, cast=True)` at I/O boundaries; `cast=False` for internal handoffs where types must already be exact.

```python
import dataframely as dy

class TurbulenceSchema(dy.Schema):
    """Long-format turbulence intensity results."""
    wind_speed_bin = dy.Int64(nullable=False)
    height = dy.Float64(nullable=False)
    interpolation_marker = dy.String(nullable=True)
    mean_ti = dy.Float64(nullable=False)
    std_ti = dy.Float64(nullable=False)
    representative_ti = dy.Float64(nullable=False)
    iec_category = dy.String(nullable=False)
    count = dy.Int64(nullable=False, min=0)


def calculate_turbulence(
    df: pl.DataFrame,
    ...
) -> dy.DataFrame[TurbulenceSchema]:
    result = _compute_turbulence(df)
    return TurbulenceSchema.validate(result, cast=True)
```

In the current codebase this pattern appears throughout `reporting/subdomains/<domain>/model/schemas.py` (e.g. `AirDensitySchema`, `TurbulenceSchema`, `WindRoseSchema`) and at function boundaries such as `calculate_ti_matrix -> dy.DataFrame[TIMatrixSchema]`.

Only skip the schema when the column set is truly dynamic (e.g. raw mast timeseries loaded from Parquet, where the available sensors vary per mast). In that case build the schema dynamically from `SensorColumn` metadata, as shown below.

### When Loading External Data (Dynamic Schema from Sensors)

DataFrames loaded from Parquet carry `SensorColumn` metadata. Validate against it:

```python
import dataframely as dy
import hashlib

from cleanmast.subdomains.dataingestion.value_objects import SensorColumn

def _hash_sensors(sensors: list[SensorColumn]) -> str:
    """Generate 6-char hash from sensor metadata for unique schema naming."""
    sensor_str = ",".join(sorted(s.column_name for s in sensors))
    return hashlib.sha256(sensor_str.encode()).hexdigest()[:6]

def create_wind_schema(
    sensors: list[SensorColumn],
    mast_name: str | None = None,
) -> type[dy.Schema]:
    """Dynamically create a dataframely Schema from SensorColumn metadata.

    Uses type() metaclass to build the schema at runtime. This is necessary
    because the column set is dynamic (depends on the mast's sensor inventory).
    The schema name includes mast_name or a sensor hash for debugging.

    - timestamp: Required, non-nullable
    - Sensor columns: All nullable Float64 (data gaps are expected)
    """
    fields: dict[str, dy.Column] = {"timestamp": dy.Datetime(nullable=False)}

    for sensor in sensors:
        fields[sensor.column_name] = dy.Float64(nullable=True)

    schema_name = f"WindSchema_{mast_name}" if mast_name \
        else f"WindSchema_{_hash_sensors(sensors)}"

    return type(schema_name, (dy.Schema,), fields)


def load_and_validate(
    df: pl.DataFrame,
    sensors: list[SensorColumn],
    mast_name: str | None = None,
) -> pl.DataFrame:
    """Validate timeseries DataFrame against sensor metadata.

    Uses cast=True so integer timestamps are auto-cast to Datetime.
    IMPORTANT: cast=True is forgiving — it coerces types silently.
    For strict validation (rejecting wrong types), use cast=False.
    """
    WindSchema = create_wind_schema(sensors, mast_name)
    return WindSchema.validate(df, cast=True)
```

### When to Use cast=True vs. cast=False

| `cast=True` | `cast=False` |
|---|---|
| I/O boundaries where upstream may produce integer timestamps or wide numeric types | Internal function boundaries where types must be exact |
| Data comes from Parquet/CSV with type ambiguity | Data flows between your own functions with known schemas |
| "Normalize into a known shape" | "Reject anything that doesn't match" |

### Fixed-Schema Return Types

Use `dy.DataFrame[Schema]` typing for functions that must return a known shape:

```python
class TIMatrixSchema(dy.Schema):
    """TI matrix: one row per wind-speed bin, columns = 16 direction sectors."""
    v_max = dy.Float64(nullable=False)
    N    = dy.Float64(nullable=False, min=0.0, max=1.0)
    NNE  = dy.Float64(nullable=False, min=0.0, max=1.0)
    NE   = dy.Float64(nullable=False, min=0.0, max=1.0)
    # ... remaining sectors

def calculate_ti_matrix(
    df: pl.DataFrame,
    wind_speed_bins: list[float],
) -> dy.DataFrame[TIMatrixSchema]:
    result = _compute_matrix(df, wind_speed_bins)
    return TIMatrixSchema.validate(result, cast=True)
```

## Anti-Patterns Checklist

Before committing Polars code:

- [ ] No `iter_rows()` in loops — use vectorized expressions
- [ ] No `df["col"]` in transformations — use `pl.col("col")`
- [ ] No `df["col"][0]` scalar extraction — use `.item()` for single values, `.to_series()` only when unavoidable
- [ ] No building expressions with `+=` in loops — use `sum([...], pl.lit(0.0))`
- [ ] No `to_numpy()` unless truly necessary (matplotlib/plotting)
- [ ] Multiple `with_columns()` calls merged into one
- [ ] No `dtypes=` in `read_csv`/`scan_csv` — use `schema_overrides=`
- [ ] No `collect(streaming=True)` — use `collect(engine="streaming")`
- [ ] No `pl.Utf8` — use `pl.String`
- [ ] No `pl.NUMERIC_DTYPES` — use `polars.selectors.numeric()`
- [ ] No bare `pl.DataFrame` return when the output shape is a contract — define a `dy.Schema` and `dy.DataFrame[Schema]` return type, then validate before returning

## Pattern Reference

| Task | Pattern |
|------|---------|
| Add calculated column | `with_columns(expr.alias("new"))` |
| Multiple columns | `with_columns(expr1.alias("a"), expr2.alias("b"))` |
| Conditional logic | `pl.when(cond).then(a).otherwise(b)` |
| Group statistics | `group_by().agg([...])` |
| Row-over-row within group | `.over(partition)` |
| Multi-column operations | `sum(pl.col(c) for c in cols)` |
| Row-wise max/mean/sum | `pl.max_horizontal(...)` / `pl.mean_horizontal(...)` / `pl.sum_horizontal(...)` |
| Clamp values | `.clip(lower_bound, upper_bound)` |
| Deg to rad | `pl.col("wd").radians()` |
| Rad to deg | `.degrees()` |
| Vector component | `.radians().sin()` / `.radians().cos()` |
| Lazy evaluation | `scan_parquet().filter().select().collect()` |
| Streaming collect | `collect(engine="streaming")` |
| Empty typed DF | `pl.Series([], dtype=pl.Float64)` per column |
| Known-shape output | Define `dy.Schema`, return `dy.DataFrame[Schema]`, and `Schema.validate(df, cast=True)` |
| Return-type contract | `-> dy.DataFrame[MySchema]` |

## References

Load these for detailed guidance when needed:
- `references/best_practices.md` — Performance optimization, pitfalls, operation reference, and code organization
