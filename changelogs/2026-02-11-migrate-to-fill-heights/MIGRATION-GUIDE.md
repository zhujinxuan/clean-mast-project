# Migration Guide: extrapolate → fill_heights

## Overview

The `extrapolate` module has been replaced with the new `fill_heights` module. This guide helps you migrate existing configurations and workflows.

## Breaking Changes

### 1. CLI Commands

**Old:**
```bash
uv run cleanmast recommend extrapolate projects/my-project -h 120,140,160
uv run cleanmast extrapolate projects/my-project
```

**New:**
```bash
uv run cleanmast recommend fill-heights projects/my-project -h 120,140,160
uv run cleanmast fill-heights projects/my-project
```

### 2. Removed Options

**Removed:** `--output-dir`

**New Behavior:** Output directories are automatically created:
- `reconstruct-meso-fill-heights/`
- `representative-year-fill-heights/`

### 3. Configuration Changes

**Old format** (extrapolate):
```toml
[vertical-extrapolate]
heights = [120, 140, 160]
output_dir = "extrapolated"
```

**New format** (fill-heights):
```toml
# Generated automatically by "recommend fill-heights"
# Two configs generated:
# - fill-heights-reconstruct-meso.toml
# - fill-heights-representative-year.toml
```

## New Features

### 1. Configurable deg_diff_limit
```bash
uv run cleanmast recommend fill-heights projects/my-project -h 120,140,160 --deg-diff-limit 0.5
```

### 2. Default Heights Changed
- **Old:** 120, 140, 160
- **New:** 125, 140, 160

### 3. WS Filtering for WD
WD fitting now filters by wind speed > 2.5 m/s at nearby sensor for reliability.

## Migration Steps

### Step 1: Update Scripts
Replace all `extrapolate` commands with `fill-heights`:
```bash
# Find all occurrences
grep -r "extrapolate" scripts/

# Replace
sed -i 's/recommend extrapolate/recommend fill-heights/g' scripts/*.sh
sed -i 's/extrapolate$/fill-heights/g' scripts/*.sh
```

### Step 2: Remove Old Configs
Delete old extrapolate config files:
```bash
rm projects/*/vertical-extrapolate.toml
```

### Step 3: Generate New Configs
```bash
uv run cleanmast recommend fill-heights projects/my-project
```

### Step 4: Update Output Paths
If you have downstream processing, update paths:
```bash
# Old
./extrapolated/M01.csv

# New
./reconstruct-meso-fill-heights/M01.parquet
```

## FAQ

### Q: Can I still use the old extrapolate module?
**A:** No, it has been removed. Use `fill_heights` instead.

### Q: Will my old configs work?
**A:** No, you need to regenerate configs using `recommend fill-heights`.

### Q: Why the change?
**A:** `fill_heights` provides:
- Better architecture
- More features (interpolation, WS filtering)
- Cleaner CLI
- Polars-native performance

## Troubleshooting

### Issue: "No nearby WS sensor found"
**Solution:** Ensure you have WindSpeed sensors near your WindDirection sensors (within 20m height difference).

### Issue: Tests failing after migration
**Solution:** Update your test fixtures to use `fill_heights` instead of `extrapolate`.

## Support

For issues or questions:
1. Check the ADRs in this changelog directory
2. Review updated documentation in `docs/python/cleanmast/fill-heights.md`
3. Check `CLAUDE.md` for Polars best practices
