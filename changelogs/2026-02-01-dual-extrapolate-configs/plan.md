# Plan: Dual Vertical Extrapolation Config Output

**Status: COMPLETED**

## Summary

Change the vertical extrapolation recommend command to output **two separate
config files** instead of one:

1. `vertical-extrapolate-reconstruct-meso.toml` - extrapolates reconstruct-meso
   output data
2. `vertical-extrapolate-representative-year.toml` - extrapolates
   representative-year output data

Both configs use the **same shear profiles** fitted from reconstruct-meso data.

## Current Behavior

- `recommend vertical-extrapolate` reads `reconstruct-meso.toml`
- Fits shear from reconstruct-meso output timeseries
- Outputs single `vertical-extrapolate.toml`
- Input: `mast.output` from reconstruct-meso
- Output: `extrapolated/{mast.name}.csv`

## New Behavior

### Output File 1: `vertical-extrapolate-reconstruct-meso.toml`

- Input: `mast.output` from `reconstruct-meso.toml`
- Output: `extrapolated-reconstruct-meso/{mast.name}.csv`
- Shear: Fitted from reconstruct-meso timeseries (same as now)

### Output File 2: `vertical-extrapolate-representative-year.toml`

- Input: `mast.output` from `representative-year.toml`
- Output: `extrapolated-representative-year/{mast.name}.csv`
- Shear: **Same values** as file 1 (fitted from reconstruct-meso, NOT from
  representative-year data)

## Implementation Steps

### 1. Update CLI to accept representative-year config path

File: `packages/cleanmast/src/cleanmast/cli.py`

- Add optional `--representative-year-config` parameter to
  `recommend vertical-extrapolate` command
- Default: `representative-year.toml` in same directory as reconstruct-meso
  config

### 2. Create model for RepresentativeYearConfiguration

File: `packages/cleanmast/src/cleanmast/models/representative_year.py` (new)

- Define Pydantic models matching Julia's `RepresentativeYearConfig.jl`:
  - `RepresentativeYearMesoModel`
  - `RepresentativeYearMast` (with `input`, `output`, `time_range`,
    `meso_model`)
  - `RepresentativeYearConfiguration`

### 3. Update recommend strategy interface

File: `packages/cleanmast/src/cleanmast/extrapolate/recommend/registry.py`

- Update `RecommendStrategy.recommend()` signature to return two configs
- Or create new method that returns dict of config name -> config

### 4. Update Top3ConstantShearStrategy

File:
`packages/cleanmast/src/cleanmast/extrapolate/recommend/top3_constant_shear.py`

Changes:
- Accept optional `representative_year_config` parameter
- Fit shear from reconstruct-meso data (unchanged)
- Build two `ExtrapolateConfiguration` objects:
  1. For reconstruct-meso: input from `reconstruct_config.masts[i].output`
  2. For representative-year: input from `rep_year_config.masts[i].output`
- Both use same fitted shear values
- Return both configs (or write both files)

### 5. Update config output paths

File: `packages/cleanmast/src/cleanmast/extrapolate/config.py`

- Add helper function to save config to TOML file
- Support different output directory names

### 6. Update tests

Files:
- `packages/cleanmast/tests/extrapolate/recommend/test_top3_constant_shear.py`
- Add new test for dual config generation
- Verify both configs have same shear values
- Verify input/output paths are correct for each config

## File Changes Summary

| File | Change Type |
|------|-------------|
| `cli.py` | Modify |
| `models/representative_year.py` | New |
| `models/__init__.py` | Modify |
| `extrapolate/recommend/registry.py` | Modify |
| `extrapolate/recommend/top3_constant_shear.py` | Modify |
| `extrapolate/config.py` | Modify |
| `tests/extrapolate/recommend/test_top3_constant_shear.py` | Modify |

## Edge Cases

1. **Mast name mismatch**: Representative-year may have different mast names
   than reconstruct-meso. Strategy: match by name, skip masts not found in both.

2. **Missing representative-year config**: If not provided, only generate the
   reconstruct-meso config file (backward compatible).

3. **Different mast counts**: Handle case where representative-year has
   fewer/more masts than reconstruct-meso.
