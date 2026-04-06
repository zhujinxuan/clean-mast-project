# Polars Type Fix - Task 1 (Canary)

## Date: 2025-04-03
## File: timeseries.py

### Problem
Polars type errors when calling `.min()` and `.max()` on datetime columns. These methods return broad union types that don't narrow properly for subsequent operations like `.strftime()`.

### Solution Pattern
```python
# BEFORE (type error)
time_min = high_df["timestamp"].min()
time_max = high_df["timestamp"].max()
# ...
return f"...{time_min.strftime('%Y年%m月%d日')}..."  # Error: Item "date" has no attribute "strftime"

# AFTER (fixed)
time_min = high_df["timestamp"].dt.min()
time_max = high_df["timestamp"].dt.max()
# ...
assert isinstance(time_min, datetime) and isinstance(time_max, datetime)
return f"...{time_min.strftime('%Y年%m月%d日')}..."  # OK
```

### Key Insights
1. The `.dt` accessor returns narrower types: `date | datetime | timedelta | None`
2. Use `isinstance(val, datetime)` narrowing before calling datetime-specific methods
3. For numeric aggregations, use `float(val or 0)` pattern (different from datetime)

### Verification
- Command: `uv run ty check packages/cleanmast`
- Result: 0 errors in timeseries.py (other pre-existing errors in other files)

### Related Pattern (Numeric)
For numeric columns like `.mean()`, `.max()`, `.min()`:
```python
mean_speed = float(high_df["wind_speed"].mean() or 0)
```

# Polars Type Fix - Task 2 (Wind Range Summary)

## Date: 2025-04-03
## File: wind_range_summary.py

### Problem
Polars `.mean()` returns a broad union type that includes non-numeric types like `date`, `timedelta`, etc. This causes ty errors when passing the result to `float()`.

### Solution Pattern
```python
# BEFORE (type error)
avg_freq = float(sorted_df["frequency_sum"].mean() or 0)
# Error: Expected ConvertibleToFloat, found complex union type

# AFTER (fixed)
from typing import cast
avg_freq = float(cast(float, sorted_df["frequency_sum"].mean()) or 0)
```

### Key Insights
1. For Polars aggregations like `.mean()`, the return type is a broad union: `int | float | Decimal | date | datetime | timedelta | time | str | bool | None`
2. `float(val or 0)` alone is NOT enough - ty still sees the broad union
3. Need `cast(float, ...)` to narrow the type BEFORE passing to `float()`
4. Pattern: `float(cast(float, series.mean()) or 0)`

### Verification
- Command: `uv run ty check packages/cleanmast/src/cleanmast/subdomains/assessment/domain/entities/single_mast/wind_range_summary.py`
- Result: All checks passed (0 errors in file)

### Applied To
- Line 117: `avg_freq = float(cast(float, sorted_df["frequency_sum"].mean()) or 0)`
- Line 118: `avg_hours = float(cast(float, sorted_df["hours"].mean()) or 0)`
- Line 119: `avg_power_freq = float(cast(float, sorted_df["power_frequency_sum"].mean()) or 0)`
- Line 120: `avg_power_hours = float(cast(float, sorted_df["power_hours"].mean()) or 0)`


# Polars Type Fix - Task 2 (wind_shear_table.py)

## Date: 2025-04-03
## File: wind_shear_table.py

### Problem
Polars `.mean()` returns complex union type `(int & ~AlwaysFalsy) | (float & ~AlwaysFalsy) | (Decimal & ~AlwaysFalsy) | ...` that `float()` constructor cannot accept directly.

### Solution Pattern
```python
# BEFORE (type error)
overall_mean = sorted_df["alpha_mean"].mean()  # Complex union type
if overall_mean > 0.25:  # Error: Union type incompatible with comparison

# AFTER (fixed)
_mean_val: Any = sorted_df["alpha_mean"].mean()
overall_mean = float(cast(float | int, _mean_val)) if _mean_val is not None else 0.0
# Now overall_mean is float, comparisons work fine
```

### Key Insights
1. Polars aggregations return very broad union types that don't narrow well
2. `float(val or 0)` pattern doesn't work due to type checker limitations
3. Use intermediate `Any` variable + explicit `cast()` + None check pattern
4. The `cast()` is necessary because `float()` constructor expects narrow types

### Verification
- Command: `uv run ty check packages/cleanmast/src/cleanmast/subdomains/assessment/domain/entities/single_mast/wind_shear_table.py`
- Result: All checks passed

### Pattern for Complex Union Types
```python
from typing import Any, cast

# For Polars aggregations with complex return types:
_raw_val: Any = df["column"].mean()  # or .min(), .max(), etc.
val = float(cast(float | int, _raw_val)) if _raw_val is not None else 0.0
```

---

# Polars Type Fix - Task 2 (Weibull Distribution)

## Date: 2025-04-03
## File: weibull_distribution.py

### Problem
Polars type errors when calling `.mean()` on Series/DataFrame columns. These methods return broad union types that don't narrow properly for subsequent operations like comparisons (`<`) or power operators (`**`).

### Solution Pattern
```python
# BEFORE (type error)
rmse = ((observed - fitted) ** 2).mean() ** 0.5  # Error: Operator `**` not supported
avg_k = fit_df["shape_k"].mean()  # Error: Can't compare with float
if avg_k < 1.5:  # Error: Operator `<` not supported

# AFTER (fixed - using cast)
from typing import cast

rmse = cast(float, ((observed - fitted) ** 2).mean() or 0) ** 0.5
avg_k = cast(float, fit_df["shape_k"].mean() or 0)
avg_c = cast(float, fit_df["scale_c"].mean() or 0)
avg_rmse = cast(float, fit_df["rmse"].mean() or 0)
```

### Key Insights
1. For numeric aggregations on Polars Series/DataFrames, `cast(float, val or 0)` is more effective than `float(val or 0)`
2. The `float()` constructor doesn't accept Polars' union return types (includes date, Decimal, etc.)
3. `cast()` from `typing` module forces the type without runtime overhead
4. The `or 0` pattern handles None values safely while cast handles the type narrowing

### Error Locations Fixed
- Line 172: `**` operator on PythonLiteral (RMSE calculation)
- Lines 191-192: Comparison operators on shape/scale parameters
- Lines 205-210: Comparison operators on RMSE thresholds

### Verification
- Command: `uv run ty check packages/cleanmast/src/cleanmast/subdomains/assessment/domain/entities/single_mast/weibull_distribution.py`
- Result: 0 errors


---

# Polars Type Fix - Task 2 (Turbulence Files)

## Date: 2025-04-03
## Files: turbulence_summary.py, turbulence_sector.py

### Problem
Polars type errors when calling `.mean()` on numeric columns. The return type is a broad union including `int | float | Decimal | date | ...` which doesn't satisfy `float()` constructor.

### Solution Pattern
```python
from typing import cast

# BEFORE (type error)
avg_mean_ti = sorted_df["mean_ti"].mean()  # Returns broad union type

# AFTER (fixed)
_mean_ti_val = cast(float | None, sorted_df["mean_ti"].mean())
avg_mean_ti = float(_mean_ti_val or 0)
```

### Key Insights
1. Polars `.mean()` returns `int | float | Decimal | date | ... | None` union type
2. `float()` constructor can't accept this broad union
3. Use `cast(float | None, ...)` to narrow the type before passing to `float()`
4. The `or 0` handles the None case safely

### Verification
- Command: `uv run ty check packages/cleanmast`
- Result: 0 errors in turbulence_summary.py and turbulence_sector.py
- Pre-existing errors in other files remain (88 total, unrelated to this fix)

### Related Pattern (Numeric Aggregations)
For any numeric aggregation like `.mean()`, `.max()`, `.min()` on Polars columns:
```python
from typing import cast

mean_val = float(cast(float | None, series.mean()) or 0)
max_val = float(cast(float | None, series.max()) or 0)
min_val = float(cast(float | None, series.min()) or 0)
```
