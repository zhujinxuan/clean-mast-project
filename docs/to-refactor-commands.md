# Remaining Commands to Refactor

## Overview

This document outlines the remaining commands that need to be refactored to follow the two-step pattern (recommend → process with TOML configuration).

### Completed Commands ✅
1. **parse-sensors** - Already follows the pattern
2. **process-clean** - Already follows the pattern  
3. **tower-shading** - Refactored
4. **reconstruct-single** - Refactored
5. **train-meso** - Refactored (fixed to match type structure)
6. **reconstruct-meso** - Refactored (due to load_model dependency)
7. **representative-year** - Refactored (due to load_model dependency)

### Commands to Refactor ❌
1. **wt-timeseries**

---

## 1. ReconstructMeso Refactoring ✅ COMPLETED

### What Was Done
- Moved `src/ReconstructMeso.jl` to `src/ReconstructMeso/Core.jl`
- Created `CommandReconstructMeso.jl` with local `load_model` function
- Created `RecommendReconstructMesoCommand.jl` that reads from train-meso.toml
- Updated all references in CleanMastCli.jl and ProcessAll.jl
- Created documentation at `docs/reconstruct-meso.md`

### Key Changes
- Model paths now: `./meso-models/{mast-name}/{meso-name}/{windspeed|winddirection}/{method}.jld2`
- Output path: `./reconstruct-meso/`
- Sources tracked in: `process-stats/reconstruct-meso-sources-{mast}.csv`
- **Important**: Fixed structure to match types - uses `masts` and `meso` arrays, not `reconstructions`

#### Step 1: Move Core Logic
- Keep `src/ReconstructMeso.jl` as is (core reconstruction logic)
- Create `src/ReconstructMeso/` directory (if needed)

#### Step 2: Create CommandReconstructMeso
Location: `src/ReconstructMeso/CommandReconstructMeso.jl`

Should:
- Read from `reconstruct-meso.toml`
- Load mast data from configured paths
- Load meso data from configured paths
- Load models from new paths: `./meso-models/{mast-name}/{meso-name}/{windspeed|winddirection}/{method}.jld2`
- Apply reconstruction for specified time range
- Save to `./reconstruct-meso/`

#### Step 3: Create RecommendReconstructMesoCommand
Location: `src/ReconstructMeso/RecommendReconstructMesoCommand.jl`

Should:
- Read `train-meso.toml` to find available models
- Generate `reconstruct-meso.toml` with:
  - Model paths
  - Time range (default or from config)
  - Output paths

#### Step 4: Update References
- Remove old command from `src/Command/`
- Update `CleanMastProject.jl`
- Update `CleanMastCli.jl` 
- Update `ProcessAll.jl`

#### Step 5: Create Documentation
Create `docs/reconstruct-meso.md`

---

## 2. RepresentativeYear Refactoring ✅ COMPLETED

### What Was Done
- Moved `src/RepresentativeYear.jl` to `src/RepresentativeYear/Core.jl`
- Created `CommandRepresentativeYear.jl` with local `load_model` function
- Created `RecommendRepresentativeYearCommand.jl` that reads from reconstruct-meso.toml
- Updated all references in CleanMastCli.jl and ProcessAll.jl
- Created documentation at `docs/representative-year.md`

### Key Changes
- Now uses 16-sector model (not 1-sector) for better directional calibration
- Output path: `./representative-year/`
- Calibration info saved to: `process-stats/representative-year-info-{mast}.yaml`
- **Important**: Fixed structure to match types - uses `masts` and `meso` arrays, not `calibrations`

#### Step 1: Create Module Structure
- Move `src/RepresentativeYear.jl` to `src/RepresentativeYear/Core.jl`
- Create module directory

#### Step 2: Create CommandRepresentativeYear
Location: `src/RepresentativeYear/CommandRepresentativeYear.jl`

Should:
- Read from `representative-year.toml`
- Load reconstructed meso data
- Load only windspeed models (1-sector)
- Apply calibration for specified time range
- Save to `./representative-year/`

#### Step 3: Create RecommendRepresentativeYearCommand
Location: `src/RepresentativeYear/RecommendRepresentativeYearCommand.jl`

Should:
- Read `reconstruct-meso.toml` to get data paths
- Read `train-meso.toml` to find 1-sector windspeed models
- Generate `representative-year.toml`

#### Step 4: Update References
Same pattern as above

#### Step 5: Create Documentation
Create `docs/representative-year.md`

---

## 3. TrainMeso Refactoring ✅ COMPLETED

### What Was Done
- Fixed type/code mismatch by updating both commands to match type structure
- `RecommendTrainMesoCommand` now generates individual model entries with correct field names
- `CommandTrainMeso` now works with the type's expected structure
- Used functional patterns (map/mapreduce) instead of for loops with push

### Key Changes
- TOML now has individual [[models]] entries (one per method)
- Each model entry has: `mast_name`, `meso_name`, `method`, `output`
- No more grouped windspeed/winddirection arrays
- Full output paths specified in TOML
- Documentation updated to show new structure

---

## 4. WtTimeSeries Refactoring

### Current State
- Location: `src/Command/WtTimeSeries.jl`
- Uses ProjectConfig from config.yaml
- Reads from `representative_year/` directory
- Outputs wind turbine time series at specific height
- Saves to configured output directory

### Refactoring Plan

#### Step 1: Create CommandWtTimeSeries
Location: `src/Command/WtTimeSeries.jl` (keep in Command as it's simple)

Modify to:
- Read from `wt-timeseries.toml`
- Process each mast configuration
- Save to configured output paths

#### Step 2: Create RecommendWtTimeSeriesCommand
Location: `src/Command/RecommendWtTimeSeriesCommand.jl`

Should:
- Read `representative-year.toml` to get data paths
- Generate `wt-timeseries.toml` with:
  - Input paths from representative year
  - Target height (from config or default)
  - Output directory

#### Step 3: Update References
- Update `CleanMastCli.jl`
- Update `ProcessAll.jl`

#### Step 4: Create Documentation
Create `docs/wt-timeseries.md`

---

## Common Patterns to Follow

### File Structure
```
src/{Module}/
├── Core.jl                    # Original logic (if exists)
├── Command{Name}.jl           # Process command
└── Recommend{Name}Command.jl  # Recommend command
```

### Import Pattern for Core Module
```julia
module {Module}
  include("./{Module}/Core.jl")
  include("./{Module}/Command{Name}.jl")
  include("./{Module}/Recommend{Name}Command.jl")
  export ... # Core exports
  export Command{Name}, Recommend{Name}Command
end
```

### TOML Configuration Loading
```julia
config_dict = load_dict(config_path)
config = from_dict({ConfigType}, config_dict)
project_dir = dirname(config_path)
```

### Path Resolution
Always resolve paths relative to project directory:
```julia
data_path = joinpath(project_dir, config.input.data)
```

### Output Paths
Follow consistent naming:
- `./tower-shading/`
- `./reconstruct-single/`
- `./reconstruct-meso/`
- `./representative-year/`
- `./wt-timeseries/`

### CLI Updates
1. Add to Process module:
```julia
@cast function {command}(config_path::String)
    Command{Name}.execute(config_path)
end
```

2. Add to Recommend module:
```julia
@cast function {command}(dir::String)
    "Recommend a {command}.toml file for the project"
    Recommend{Name}Command.execute(dir)
end
```

### ProcessAll Updates
Add both recommend and process steps:
```julia
println("\n{N}. Recommending {command} config...")
Recommend{Name}Command.execute(dir)

println("\n{N+1}. Processing {command}...")
Command{Name}.execute(joinpath(dir, "{command}.toml"))
```

---

## Testing After Refactoring

For each refactored command:
1. Run the recommend command
2. Review generated TOML
3. Run the process command
4. Verify output matches previous behavior
5. Run full pipeline with `process all` 