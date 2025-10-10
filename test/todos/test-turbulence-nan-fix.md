# TODO: Tests for Turbulence NaN Fix

## Overview

Test the fix for NaN values in `meteodyn_ti_*.txt` files caused by insufficient valid TI data in sector/wind speed bins.

## Code Change Context

**Fix applied:** Changed `calculate_ti_matrix` to check for valid data count before calculating mean:

```julia
# BEFORE: Could write NaN when all TI values are missing
if nrow(sector_data) ≥ 5
    result[i, sector.name] = mean(skipmissing(sector_data.ti))
end

# AFTER: Prevents NaN by checking valid data count
valid_sector_ti = skipmissing(sector_data.ti)
if length(valid_sector_ti) ≥ 5
    result[i, sector.name] = mean(valid_sector_ti)
end
```

**Root cause:** `mean(skipmissing([]))` returns `NaN` when all TI values are `missing`, even if `nrow(sector_data) ≥ 5`.

## Test File Location

Create: `test/ReportTimeSeries/test_turbulence_nan_fix.jl`

Add to `test/runtests.jl`:
```julia
"turbulence" => [
    "ReportTimeSeries/test_turbulence_nan_fix.jl"
]
```

## Test Scenarios

### 1. NaN Prevention (Core Fix)

- [ ] All missing TI values in sector/bin (≥5 rows, all `ti` missing) → keeps `mean_ti` fallback, no NaN
- [ ] Partial missing with sufficient valid data (10 rows, 7 valid) → calculates mean from valid values
- [ ] Partial missing with insufficient valid data (10 rows, 4 valid) → keeps `mean_ti` fallback
- [ ] Exactly 5 valid values (boundary case) → calculation performed
- [ ] All valid values (no missing) → normal calculation, unchanged behavior

### 2. Matrix Fallback Logic

- [ ] Verify `mean_ti` initialization preserved when insufficient data
- [ ] Multiple sectors with mixed data quality → each handled correctly
- [ ] No NaN values written to any sector column

### 3. Integration with TI Calculation

- [ ] Missing `ws_sd` values propagate to `ti` column
- [ ] Missing `ws_avg` values propagate to `ti` column
- [ ] Formula verification: `ti = ws_sd / max(ws_avg, 1.0)`

### 4. End-to-End Workflow

- [ ] Realistic sparse data scenario (70% valid, 30% missing)
- [ ] Low wind speed bins with rare data
- [ ] Prevailing vs non-prevailing wind sectors

### 5. File Output Validation

- [ ] Generated `meteodyn_ti_*.txt` contains no "NaN" strings
- [ ] All values are valid floats
- [ ] Fallback values present where expected

## Implementation Priority

1. **HIGH**: All missing TI values test (core fix validation)
2. **HIGH**: Partial missing with insufficient valid data
3. **MEDIUM**: Matrix fallback preservation
4. **MEDIUM**: End-to-end integration test
5. **LOW**: File output validation

## Related Files

- **Source**: `src/ReportTimeSeries/Turbulence.jl` (calculate_ti_matrix, lines 165-169)
- **Functions**: calculate_ti_series, calculate_sector_stats, save_meteodyn_ti
- **Types**: `src/Types/TurbulenceIntensity.jl`
