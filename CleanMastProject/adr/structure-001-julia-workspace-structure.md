---
id: structure-001-julia-workspace-structure
name: julia-workspace-structure
description: Julia workspace pattern for CleanMast with root workspace Project.toml and CleanMastProject package directory
tags: [julia, workspace, structure, modules, include-pattern]
applies_when:
  - modifying Julia module structure
  - creating new submodules
  - understanding workspace organization
  - adding new CLI commands
---

# ADR-001: Julia Workspace Structure

## Constraint (MUST)

1. **MUST use workspace pattern**: Root `Project.toml` with `[workspace]` section pointing to `CleanMastProject`
2. **MUST keep source in CleanMastProject/src/**: All `.jl` files live under the package directory
3. **MUST use PascalCase for module directories**: `Types/`, `ParseSensors/`, `DataClean/`, etc.
4. **MUST use `include()` in main module**: `CleanMastProject.jl` loads submodules via `include("ModuleName/ModuleName.jl")`
5. **MUST wrap each submodule file in `module ... end`**: Each file defines its own module namespace
6. **MUST place CLI commands under `Command/`**: All command implementations go in `src/Command/`
7. **MUST place type definitions under `Types/`**: All core types and configurations go in `src/Types/`

### Directory Purpose Table

| Directory | Purpose | Contains |
|-----------|---------|----------|
| `Types/` | Core type definitions | Config structs, sensor types, data models |
| `ParseSensors/` | Data parsing | CSV parsing, column mapping, sensor detection |
| `DataClean/` | Data cleaning | Validation rules, range checks, outlier detection |
| `ReconstructSingleMast/` | Single-mast reconstruction | Gap filling, correlation methods |
| `ReconstructMeso/` | Mesoscale reconstruction | Meso data integration, calibration |
| `ReconstructCross/` | Cross-mast reconstruction | Multi-mast correlation |
| `Logging/` | Logging infrastructure | Logger implementations |
| `AnalyzeEN/` | EN standard analysis | IEC/EN compliance calculations |
| `RepresentativeYear/` | Long-term calibration | P50/P90, representative year |
| `TowerShading/` | Tower shadow correction | Shadow detection and correction |
| `Command/` | CLI commands | Comonicon command implementations |
| `WindSpeedModels/` | Wind speed models | Shear models, profile fitting |
| `WindDirectionModels/` | Wind direction models | Veer models, direction analysis |
| `WTTimeSeries/` | Wind turbine time series | Power curve integration |
| `TrainReconstructCross/` | Training cross-mast models | ML model training |
| `ReportTimeSeries/` | Time series reports | Report generation |
| `ReportFrozenPeriod/` | Frozen period reports | Icing reports |
| `ReportRecovery/` | Recovery reports | Data recovery reports |
| `ReportClean/` | Data cleaning reports | Cleaning analysis reports |
| `ReportReconstructSingle/` | Single mast reconstruction reports | Reconstruction analysis |
| `ReportReconstructMeso/` | Mesoscale reconstruction reports | Meso reconstruction reports |
| `ReportMesoTimeSeries/` | Mesoscale time series reports | Meso time series reports |
| `ReportReconstructCross/` | Cross-mast reconstruction reports | Cross-mast analysis reports |
| `ReportAllMasts/` | All masts reports | Comprehensive mast reports |
| `TrainMeso/` | Mesoscale training | Meso model training |
| `GuessMastFromMeso/` | Mast guessing | Meso-based mast location |
| `TimeSeriesProcessing/` | Time series processing | Generic time series ops |

## Rationale (WHY)

- **Workspace pattern**: Enables Julia's workspace feature for dependency management and cleaner project structure
- **Separation of concerns**: Each module handles one aspect of wind data processing
- **Clear CLI organization**: All commands grouped under `Command/` for discoverability
- **Type centralization**: All configurations and types in one location for consistency
- **Functional pipeline**: Module names reflect the data processing pipeline stages

## Pattern (HOW)

### Workspace Structure

```
clean-mast-project/ (root)
├── Project.toml                    # Workspace configuration
│   # [workspace]
│   # members = ["CleanMastProject"]
├── bin/
│   └── CleanMast.jl               # Entry point: activates project
├── CleanMastProject/              # Actual package
│   ├── Project.toml               # Package dependencies
│   ├── src/
│   │   ├── CleanMastProject.jl   # Main module with includes
│   │   ├── CleanMastCli.jl       # CLI entry point
│   │   ├── CleanMastUtils.jl     # Shared utilities
│   │   ├── Types/
│   │   │   └── *.jl              # Type definitions
│   │   ├── ParseSensors/
│   │   │   └── *.jl              # Parsing logic
│   │   ├── DataClean/
│   │   │   └── *.jl              # Cleaning rules
│   │   ├── Command/
│   │   │   └── *.jl              # CLI commands
│   │   └── ...other modules/
│   ├── test/
│   └── docs/
```

### Main Module Pattern

**File: `CleanMastProject/src/CleanMastProject.jl`**

```julia
module CleanMastProject

# 1. Load shared utilities first
include("CleanMastUtils.jl")
using .CleanMastUtils

# 2. Load types (needed by all other modules)
include("Types/Types.jl")
using .Types

# 3. Load data processing modules
include("ParseSensors/ParseSensors.jl")
include("DataClean/DataClean.jl")

# 4. Load reconstruction modules
include("ReconstructSingleMast/ReconstructSingleMast.jl")
include("ReconstructMeso/ReconstructMeso.jl")

# 5. Load analysis modules
include("AnalyzeTimeSeries/AnalyzeTimeSeries.jl")
include("AnalyzeEN/AnalyzeEN.jl")

# 6. Load CLI commands last (depend on everything else)
include("Command/Command.jl")

end # module
```

### Submodule Pattern

**File: `CleanMastProject/src/Types/Types.jl`**

```julia
module Types

# Export public API
export SensorColumn, MastConfig, ProcessCleanConfig

# Include individual type files
include("SensorColumns.jl")
include("MastConfig.jl")
include("ProcessCleanConfig.jl")

end # module
```

### Adding a New Module

1. Create directory: `src/NewModule/` (PascalCase)
2. Create main file: `src/NewModule/NewModule.jl`
3. Add `include("NewModule/NewModule.jl")` to `CleanMastProject.jl`
4. Add `using .NewModule` if needed by other modules

### Adding a New CLI Command

1. Create file: `src/Command/new_command.jl`
2. Implement using Comonicon: `@cast new_command(args...) ...`
3. Include in `src/Command/Command.jl`: `include("new_command.jl")`

## Anti-Pattern (AVOID)

```
# ❌ Putting source files in root src/
src/some_module.jl              # WRONG: Should be in CleanMastProject/src/

# ❌ Not using workspace pattern
Project.toml                    # Missing [workspace] section
# (no CleanMastProject subdirectory)

# ❌ Wrong directory naming
src/types/                      # WRONG: Use PascalCase Types/
src/parse_sensors/              # WRONG: Use ParseSensors/
src/data-clean/                 # WRONG: Use DataClean/

# ❌ Missing module wrapper
# File: src/Types/SensorColumns.jl
struct SensorColumn ... end      # WRONG: Wrap in `module SensorColumns ... end`

# ❌ Direct file includes without module
include("some_random_file.jl")   # WRONG: Include module files that wrap content

# ❌ Business logic in Command/
Command/data_processing.jl      # WRONG: Logic belongs in DataClean/ or domain module

# ❌ Types scattered across modules
DataClean/SomeConfig.jl         # WRONG: Configs belong in Types/

# ❌ Deep nesting
src/Processing/Data/Clean/Rules.jl   # WRONG: Max 2 levels, use DataClean/Rules.jl
```

## Phase Links

Detailed guidance by workflow phase:

| Phase | File | Purpose |
|-------|------|---------|
| **Plan** | [`phases/structure-001-julia-workspace-structure/on-plan.md`](./phases/structure-001-julia-workspace-structure/on-plan.md) | Module structure design guidance |
| **Review Plan** | [`phases/structure-001-julia-workspace-structure/review-plan.md`](./phases/structure-001-julia-workspace-structure/review-plan.md) | Structure review checklist |
| **Code** | [`phases/structure-001-julia-workspace-structure/code.md`](./phases/structure-001-julia-workspace-structure/code.md) | Implementation patterns |
| **Review Implementation** | [`phases/structure-001-julia-workspace-structure/review-implementation.md`](./phases/structure-001-julia-workspace-structure/review-implementation.md) | Code review checklist |

## Validation

```bash
#!/bin/bash

echo "=== ADR-001 Julia Workspace Structure Validation ==="

# Check workspace pattern
if [ ! -f "Project.toml" ]; then
    echo "FAIL: Missing root Project.toml"
    exit 1
fi

if ! grep -q "\[workspace\]" Project.toml; then
    echo "FAIL: Root Project.toml missing [workspace] section"
    exit 1
fi

if [ ! -d "CleanMastProject" ]; then
    echo "FAIL: Missing CleanMastProject directory"
    exit 1
fi

# Check main module exists
if [ ! -f "CleanMastProject/src/CleanMastProject.jl" ]; then
    echo "FAIL: Missing CleanMastProject/src/CleanMastProject.jl"
    exit 1
fi

# Check for PascalCase directories
for dir in CleanMastProject/src/*/; do
    dirname=$(basename "$dir")
    if [[ ! "$dirname" =~ ^[A-Z][a-zA-Z]*$ ]]; then
        echo "WARN: Directory not PascalCase: $dirname"
    fi
done

# Check Types/ directory exists
if [ ! -d "CleanMastProject/src/Types" ]; then
    echo "WARN: Missing Types/ directory"
fi

# Check Command/ directory exists
if [ ! -d "CleanMastProject/src/Command" ]; then
    echo "WARN: Missing Command/ directory"
fi

echo "✓ Julia workspace structure validation passed"
```

## References

- Julia workspaces: https://pkgdocs.julialang.org/v1/environments/#Project-and-Manifest
- Julia modules: https://docs.julialang.org/en/v1/manual/modules/
- Comonicon CLI: https://comonicon.org/
- Related ADRs:
  - `cli-001-comonicon-patterns.md` - CLI command patterns
  - `types-001-julia-type-patterns.md` - Type definition patterns

---

**Next ADRs to discuss:**
- CLI patterns for Comonicon commands
- Type definition patterns for Julia
