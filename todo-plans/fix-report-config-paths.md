# TODO: Fix Report Configuration Path Handling

## Problem

All report configuration files currently specify paths relative to **project directory**, not relative to the **TOML file location**. This violates the principle of location-independent configuration files.

## Current Behavior

Config file at: `projects/my-project/report-masts/report-cross-mast.toml`

```toml
[[masts]]
name = "M230016"
[masts.input]
data_file = "reconstruct-single/M230016.csv"  # Relative to projects/my-project/, NOT to report-masts/
sensors_file = "sensors.toml"                  # Relative to projects/my-project/, NOT to report-masts/

[analyze]
output_dir = "./report-masts/cross-mast"       # Relative to projects/my-project/
```

## Expected Behavior

Paths should be relative to the TOML file:

```toml
[[masts]]
name = "M230016"
[masts.input]
data_file = "../reconstruct-single/M230016.csv"  # Relative to report-masts/
sensors_file = "../sensors.toml"                  # Relative to report-masts/

[analyze]
output_dir = "./cross-mast"  # Relative to report-masts/
```

## Affected Files

All report configurations under `report-masts/`:
- `report-recovery.toml`
- `report-cross-mast.toml`
- `report-reconstruct-single.yaml`
- `report-reconstruct-meso.toml`
- `report-timeseries-meso.toml`
- `report-timeseries-rep.toml`

## Impact

### Command Files to Update
1. All `Recommend*Command.jl` files that generate report configs
2. All `Command*.jl` / `Report*.jl` files that read report configs

### Logic Changes
Current:
```julia
config_dir = dirname(config_path)
project_dir = if basename(config_dir) == "report-masts"
    dirname(config_dir)  # Go up to project root
else
    config_dir
end
# Then use project_dir as base for all paths
```

Should be:
```julia
config_dir = dirname(config_path)
# Use config_dir as base for all paths (files are relative to TOML location)
```

## Priority

Medium - This is a design consistency issue, but not breaking functionality. All existing reports work correctly, they just use project-relative paths instead of config-relative paths.

## Estimated Effort

- ~12 recommend commands to update
- ~6 report command files to update
- All path generation logic in recommend commands
- All path resolution logic in report commands
- Testing with actual project structures

## When to Fix

After stabilizing the current report implementations. This requires coordinated changes across many files and careful testing to avoid breaking existing projects.
