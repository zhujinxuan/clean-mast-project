# Task 1 Discovery: wt_timeseries Import Status

**Date**: 2026-03-17  
**Task**: Verify wt_timeseries import status  
**Status**: ACTIVE - Not orphaned, actively used via CLI

---

## Summary

**wt_timeseries is NOT orphaned** - it is actively registered in CLI but NOT imported as a module anywhere.

---

## Import Analysis

### Absolute Imports
- **Count**: 0
- **Pattern**: `from cleanmast.wt_timeseries` or `import cleanmast.wt_timeseries`
- **Result**: No absolute imports found

### Relative Imports
- **Count**: 0
- **Pattern**: `from .wt_timeseries` or `from ..wt_timeseries`
- **Result**: No relative imports found

### CLI Registration
- **Count**: 2 commands registered
- **Location**: `packages/cleanmast/src/cleanmast/cli.py` (lines 69-70)
- **Commands**:
  - `recommend_wt_timeseries_cli` (line 69)
  - `execute_wt_timeseries_cli` (line 70)

---

## CLI Import Chain

```
cli.py
  → imports from .adapters.cli:
    - recommend_wt_timeseries_cli
    - execute_wt_timeseries_cli

adapters/cli/__init__.py
  → imports:
    - from .recommend_wt_timeseries import recommend_wt_timeseries_cli
    - from .generate_wt_timeseries import execute_wt_timeseries_cli
```

**CLI adapter files using wt_timeseries domain logic**:
- `adapters/cli/recommend_wt_timeseries.py`
- `adapters/cli/generate_wt_timeseries.py`

---

## Files Referencing wt_timeseries (21 total)

### Core Module Files (3):
- `wt_timeseries/config.py`
- `wt_timeseries/core.py`
- `wt_timeseries/turbulence.py`

### Domain Logic Files (6):
- `application/usecases/recommend_wt_timeseries.py`
- `application/usecases/generate_wt_timeseries.py`
- `subdomains/dataprocessing/services/wt_timeseries_generator.py`
- `subdomains/dataprocessing/services/turbulence_calculator.py`
- `subdomains/configuration/value_objects/wt_timeseries_config.py`
- `subdomains/pipeline/services/pipeline_orchestrator.py`

### CLI Adapter Files (2):
- `adapters/cli/recommend_wt_timeseries.py`
- `adapters/cli/generate_wt_timeseries.py`

### Subdomain __init__ Files (7):
- `subdomains/__init__.py`
- `subdomains/dataprocessing/__init__.py`
- `subdomains/dataprocessing/services/__init__.py`
- `subdomains/dataprocessing/commands/__init__.py`
- `subdomains/dataprocessing/commands/recommend.py`
- `subdomains/dataprocessing/commands/execute.py`
- `subdomains/configuration/__init__.py`
- `subdomains/configuration/value_objects/__init__.py`

### Other (3):
- `cli.py`
- `adapters/cli/__init__.py`

---

## Decision Required (for Task 7)

**Question**: How to handle wt_timeseries in the cleanup?

**Options**:
1. **Keep as-is**: The CLI adapters work directly without importing the `wt_timeseries` package itself
2. **Properly expose**: Add `wt_timeseries` to `cleanmast/__init__.py` for consistency with other subpackages
3. **Merge into subdomains**: Move `wt_timeseries/` content into appropriate subdomains (e.g., `dataprocessing/`)

**Recommendation**: Option 2 (add to `__init__.py`) is the minimal fix for consistency. The module structure appears valid and well-integrated.

---

## Findings

| Check | Result | Count |
|-------|--------|-------|
| Absolute imports from cleanmast.wt_timeseries | ❌ None | 0 |
| Relative imports (from .wt_timeseries) | ❌ None | 0 |
| Import cleanmast.wt_timeseries | ❌ None | 0 |
| CLI command registration | ✅ Active | 2 commands |
| Referenced in __init__.py | ❌ No | 0 |

---

## Next Steps

**For Task 7**:
- Decision needed on whether to expose `wt_timeseries` in `cleanmast/__init__.py`
- CLI functionality is working, so this is a structural consistency issue, not a bug

---

# Task 2 Discovery: Compare io/ modules for differences

**Date**: 2025-03-17  
**Task**: Verify io/ and subdomain infrastructure/ are functionally identical  
**Status**: COMPLETED - Can safely delete io/

---

## Summary
The `io/` module and `subdomains/dataingestion/infrastructure/` contain **functionally identical** code. Differences are ONLY in import style (relative vs absolute).

---

## Diff Results

### timeseries_io.py
**Differences**: Lines 19-21 (import statements only)

```diff
- from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
- from ..subdomains.dataingestion.entities.time_series_data import TimeSeriesData
- from ..subdomains.dataingestion.value_objects.time_series_source import TimeSeriesSource
+ from cleanmast.subdomains.dataingestion.value_objects import SensorColumn
+ from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
+ from cleanmast.subdomains.dataingestion.value_objects.time_series_source import TimeSeriesSource
```

**Analysis**: 
- io/ version uses mixed imports (absolute + relative)
- subdomain version uses consistent absolute imports
- **Functionally identical**: Both import the same symbols

### timeseries_validation.py
**Differences**: Line 18 (import statement only)

```diff
- from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
+ from cleanmast.subdomains.dataingestion.value_objects import SensorColumn
```

**Analysis**:
- io/ version imports from specific submodule
- subdomain version imports from package (shorter)
- **Functionally identical**: Both import SensorColumn

---

## File Inventory

### packages/cleanmast/src/cleanmast/io/
| File | Size | Notes |
|------|------|-------|
| timeseries_io.py | 11,387 bytes | Same as subdomain version |
| timeseries_validation.py | 4,299 bytes | Same as subdomain version |
| **Missing**: __init__.py | N/A | No package marker |

### packages/cleanmast/src/cleanmast/subdomains/dataingestion/infrastructure/
| File | Size | Notes |
|------|------|-------|
| __init__.py | 598 bytes | Package marker present |
| timeseries_io.py | 11,389 bytes | Canonical version |
| timeseries_validation.py | 4,285 bytes | Canonical version |
| __pycache__/ | dir | Compiled bytecode |

---

## Files Unique to Each Location

### In io/ only (will be lost on deletion)
- **NONE** - No unique files

### In subdomain infrastructure/ only (will remain)
- `__init__.py` - Package initialization (expected to be there)

---

## Conclusion

### VERDICT: ✅ io/ can be safely deleted

| Check | Result |
|-------|--------|
| Functionally identical | ✅ Yes - All module logic identical |
| Only import differences | ✅ Yes - Just relative vs absolute |
| No unique files in io/ | ✅ Yes - Nothing will be lost |
| Subdomain has __init__.py | ✅ Yes - Proper package structure |

---

## Recommendation

**Proceed with Task 6** (delete io/ directory) after:
1. Updating any imports that reference `cleanmast.io` to use `cleanmast.subdomains.dataingestion.infrastructure`
2. Running tests to verify no breakage

---

## Commands Used

```bash
# Compare the two modules
diff packages/cleanmast/src/cleanmast/io/timeseries_io.py packages/cleanmast/src/cleanmast/subdomains/dataingestion/infrastructure/timeseries_io.py
diff packages/cleanmast/src/cleanmast/io/timeseries_validation.py packages/cleanmast/src/cleanmast/subdomains/dataingestion/infrastructure/timeseries_validation.py

# List directory contents
ls -la packages/cleanmast/src/cleanmast/io/
ls -la packages/cleanmast/src/cleanmast/subdomains/dataingestion/infrastructure/

---

# Task 3 Discovery: Inventory test fixtures (conftest.py files)

**Date**: 2026-03-17  
**Task**: Find all conftest.py files and document fixtures for test moves  
**Status**: COMPLETE

---

## Summary

Found **3 conftest.py files** in packages/cleanmast/tests/:

1. `tests/assessment/conftest.py` (146 lines)
2. `tests/fill_heights/conftest.py` (385 lines)  
3. `tests/wt_timeseries/conftest.py` (336 lines)

**No root-level `tests/conftest.py` exists** - root level does not need to stay.

---

## 1. tests/assessment/conftest.py

**Purpose:** Fixtures for assessment domain tests (ReportAtoms, wind roses, monthly patterns)

**Fixtures (9 total):**

| Fixture | Type | Dependencies | Description |
|---------|------|--------------|-------------|
| `temp_output_dir` | Path | `tmp_path` | Temporary output directory |
| `sample_mast_meta` | SingleMastMeta | - | Basic mast metadata for M01 |
| `sample_wind_rose_df` | pl.DataFrame | - | Sample wind rose data (16 sectors, 2 heights) |
| `wind_frequency_rose_atom` | Any | `sample_wind_rose_df`, `sample_mast_meta` | SingleMastMonthlyWindFrequencyRoseAtom instance |
| `wind_power_rose_atom` | Any | `sample_wind_rose_df`, `sample_mast_meta` | SingleMastWindPowerRoseAtom instance |
| `sample_monthly_wind_df` | pl.DataFrame | - | Monthly wind speed data (6 rows, 3 months) |
| `sample_monthly_wind_power_df` | pl.DataFrame | - | Monthly wind power density data |
| `monthly_wind_atom` | Any | `sample_monthly_wind_df`, `sample_mast_meta` | SingleMastMonthlyPatternAtom instance |
| `monthly_wind_power_atom` | Any | `sample_monthly_wind_power_df`, `sample_mast_meta` | SingleMastMonthlyPowerPatternAtom instance |

**Internal Dependencies:**
- `wind_frequency_rose_atom` → uses `sample_wind_rose_df`, `sample_mast_meta`
- `wind_power_rose_atom` → uses `sample_wind_rose_df`, `sample_mast_meta`
- `monthly_wind_atom` → uses `sample_monthly_wind_df`, `sample_mast_meta`
- `monthly_wind_power_atom` → uses `sample_monthly_wind_power_df`, `sample_mast_meta`

**Domain Imports:**
- `cleanmast.subdomains.assessment.domain.entities`
- `cleanmast.subdomains.assessment.domain.value_objects`

---

## 2. tests/fill_heights/conftest.py

**Purpose:** Fixtures for fill_heights module tests (height interpolation/extrapolation)

**Fixtures (7 total):**

| Fixture | Type | Dependencies | Description |
|---------|------|--------------|-------------|
| `sample_sensor_columns` | list[SensorColumn] | - | 8 sensors (WS/WD at 50/80/100m, plus max) |
| `sample_timeseries` | TimeSeriesData | `sample_sensor_columns` | 1000 rows synthetic wind data with shear |
| `sample_mast_config` | MastFillConfig | - | Config for WS/WD extrapolation to 120m |
| `sample_interpolation_ws_config` | WindSpeedHeightConfig | - | WS interpolation config for 65m from 50m/80m |
| `sample_interpolation_wd_config` | WindDirectionHeightConfig | - | WD interpolation config for 65m from 50m/80m |
| `known_shear_timeseries` | TimeSeriesData | - | Perfect power-law profile (α=0.20) |
| `wraparound_wd_timeseries` | TimeSeriesData | - | WD wraparound test data (355°→5°) |

**Internal Dependencies:**
- `sample_timeseries` → uses `sample_sensor_columns`

**Domain Imports:**
- `cleanmast.subdomains.configuration` (HeightReference, MastFillConfig, etc.)
- `cleanmast.subdomains.dataingestion.value_objects` (SensorColumn, TimeSeriesSource)
- `cleanmast.subdomains.dataingestion.entities` (TimeSeriesData)

---

## 3. tests/wt_timeseries/conftest.py

**Purpose:** Fixtures for wt_timeseries module tests (turbulence intensity, CSV generation)

**Fixtures (8 total):**

| Fixture | Type | Dependencies | Description |
|---------|------|--------------|-------------|
| `sample_turbulence_matrix` | np.ndarray | - | 28x16 matrix of TI values (0.05-0.35) |
| `synthetic_wind_timeseries` | tuple[pl.DataFrame, float] | - | 1-year synthetic data with Weibull distribution |
| `test_project_structure` | tuple[Path, Path, Path] | `tmp_path` | Project dir structure for WT tests |
| `sample_sensor_columns_with_sd` | list[SensorColumn] | - | 12 sensors (WS avg/sd, WD at 4 heights) |
| `sample_wt_timeseries_mast` | WtTimeSeriesMast | - | Config for TGL1 with heights [100,120,140] |
| `sample_parquet_with_sensors` | tuple[Path, list] | `tmp_path`, `sample_sensor_columns_with_sd` | Parquet file with embedded sensor metadata |
| `ti_test_dataframe` | pl.DataFrame | - | 10k rows with realistic TI behavior |
| `known_ti_dataframe` | tuple[pl.DataFrame, float] | - | Constant WS=10, TI=0.15 for accuracy testing |

**Internal Dependencies:**
- `sample_parquet_with_sensors` → uses `tmp_path`, `sample_sensor_columns_with_sd`
- `test_project_structure` → uses `tmp_path`

**Domain Imports:**
- `cleanmast.subdomains.dataingestion.value_objects` (SensorColumn, TimeSeriesSource)
- `cleanmast.subdomains.dataingestion.entities` (TimeSeriesData)
- `cleanmast.subdomains.configuration` (WtTimeSeriesMast)

---

## Cross-Directory Dependencies

**No cross-directory fixture dependencies detected.**

Each conftest.py is self-contained:
- ✅ `assessment` fixtures only use local fixtures + pytest built-ins
- ✅ `fill_heights` fixtures only use local fixtures + pytest built-ins  
- ✅ `wt_timeseries` fixtures only use local fixtures + pytest built-ins

**Shared Pattern:** All three use similar domain imports from:
- `cleanmast.subdomains.dataingestion.value_objects` (SensorColumn, TimeSeriesSource)
- `cleanmast.subdomains.dataingestion.entities` (TimeSeriesData)
- `cleanmast.subdomains.configuration` (various config classes)

This is expected as they all deal with sensor/time-series data.

---

## Recommendations for Test Moves (Tasks 8-10)

1. **Each conftest.py should move with its test directory** - they are self-contained
2. **No conftest.py merging needed** - no shared fixtures between directories
3. **Consider root-level conftest.py** for common fixtures like:
   - `sample_sensor_columns` (similar patterns exist in fill_heights and wt_timeseries)
   - `temp_output_dir` (used in assessment)
4. **Check tests that import from other test directories** - may need fixture relocation

---

## Files Inventory

```
packages/cleanmast/tests/
├── assessment/
│   └── conftest.py          # 146 lines, 9 fixtures
├── fill_heights/
│   └── conftest.py          # 385 lines, 7 fixtures
├── wt_timeseries/
│   └── conftest.py          # 336 lines, 8 fixtures
└── (no root conftest.py)
```

**Total Fixtures: 24** (across all conftest.py files)
```
