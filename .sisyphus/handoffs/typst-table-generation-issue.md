# Handoff Document: Typst Table Generation Issue

## Overview
During the fix for the `detect_interpolation_marker()` crash, we discovered a **pre-existing bug** in the Typst table generation that causes PDF compilation to fail.

## The Problem

### Symptoms
```
error: expected comma
    ┌─ ...\projects\kp-202603\rep-ts\report.typ:155:33
    │
155 │   [40m], [4.40], [0.335], [0.995]
    │                                  ^
```

The generated `.typ` file has **malformed tables** with missing commas between rows:
```typst
#table(
  columns: (auto, auto, auto, auto),
  inset: 8pt,
  align: center,
  table.header(
    [高度], [平均风速(m/s)], [风切变指数α], [拟合优度R²]
  ),
  [40m], [4.40], [0.335], [0.995]    // ← Missing comma
  [50m], [4.79], [0.335], [0.995]    // ← Missing comma
  ...
  [200m], [7.55], [0.335], [0.995]   // ← Extra comma after last row
,
)
```

## Root Cause

The table generation code in multiple entity files doesn't properly add commas between rows. Example from `vertical_profile.py`:

```python
# Current problematic code pattern:
lines.append(f"  [{height_str}], [{mean_ws:.2f}], [{alpha:.3f}], [{r_squared:.3f}]")

# Should be:
lines.append(f"  [{height_str}], [{mean_ws:.2f}], [{alpha:.3f}], [{r_squared:.3f}],")
```

## Affected Files

The following files generate Typst tables and likely have this issue:

| File | Table Type | Status |
|------|-----------|--------|
| `vertical_profile.py` | Vertical wind profile | ❌ Affected |
| `wind_shear_table.py` | Wind shear matrix | Likely affected |
| `wind_frequency_table.py` | Wind frequency | Likely affected |
| `wind_power_frequency_table.py` | Wind power frequency | Likely affected |
| `weibull_distribution.py` | Weibull parameters | Likely affected |
| `weibull_multi.py` | Multi-height Weibull | Likely affected |
| `wind_rose_grid.py` | Wind rose data | Likely affected |
| `monthly_pattern.py` | Monthly wind pattern | Likely affected |
| `monthly_power_pattern.py` | Monthly power pattern | Likely affected |
| `daily_pattern.py` | Daily wind pattern | Likely affected |
| `daily_power_pattern.py` | Daily power pattern | Likely affected |
| `timeseries.py` | Time series stats | Likely affected |
| `monthly_daily_wind.py` | Monthly-daily wind | Likely affected |
| `monthly_daily_power.py` | Monthly-daily power | Likely affected |
| `turbulence_intensity.py` | TI data | Likely affected |
| `turbulence_sector.py` | TI by sector | Likely affected |
| `turbulence_summary.py` | TI summary | Likely affected |
| `wind_range_summary.py` | Wind range | Likely affected |
| `weibull_parameters.py` | Weibull params | Likely affected |

## Fix Required

### Pattern to Fix
All table row generation should:
1. Add a **trailing comma** after each row
2. **Not add an extra comma** after the header
3. Ensure the closing `)` is on its own line or properly formatted

### Example Fix
```python
# In vertical_profile.py (and similar files)

# Change from:
lines.append(f"  [{height_str}], [{mean_ws:.2f}], [{alpha:.3f}], [{r_squared:.3f}]")

# To:
lines.append(f"  [{height_str}], [{mean_ws:.2f}], [{alpha:.3f}], [{r_squared:.3f}],")
```

### Alternative: Use join() pattern
```python
rows = []
for ...:
    rows.append(f"  [{height_str}], [{mean_ws:.2f}], [{alpha:.3f}], [{r_squared:.3f}]")

# Join with commas
lines.append(",\n".join(rows))
```

## Testing

1. Generate report: `uv run cleanmast report timeseries projects/kp-202603/`
2. Check `.typ` file: `projects/kp-202603/rep-ts/report.typ`
3. Verify tables have commas between rows
4. Compile manually: `typst compile projects/kp-202603/rep-ts/report.typ`

## Workaround

For immediate use, skip PDF/DOCX generation:
```bash
uv run cleanmast report timeseries projects/kp-202603/ --no-pdf --no-docx
```

The `.typ` file is generated successfully and can be compiled manually after fixing the syntax errors.

## Related Issues

- This is **separate from** the `detect_interpolation_marker()` crash we fixed
- This is **separate from** the `stat_type == "avg"` filtering issue we fixed
- This is **separate from** the TI calculation fix (using sd sensors)

## Files Modified in This Session

For reference, these files were modified for the interpolation marker fix:
1. `sensor_column.py` - Added `detect_interpolation_marker()` method
2. `wind_temporal_analyzer.py` - Added `stat_type == "avg"` filter
3. `vertical_profile_analyzer.py` - Added `stat_type == "avg"` filter
4. `turbulence_calculator.py` - Fixed TI calculation to use paired sensors
5. `monthly_daily_wind.py` - Added empty DataFrame guard
6. `turbulence_summary.py` - Added empty DataFrame guard
7. `turbulence_multi.py` - Added empty DataFrame guard

---
**Created**: 2025-04-04
**Session**: fix-report-timeseries-crash
