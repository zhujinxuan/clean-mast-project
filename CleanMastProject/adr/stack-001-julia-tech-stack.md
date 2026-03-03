---
id: stack-001-julia-tech-stack
name: julia-tech-stack
description: Julia technology stack for CleanMast wind energy data processing, including Comonicon CLI, DataFrames ecosystem, TOML configuration, and AlgebraOfGraphics visualization
status: enforced
tags: [stack, julia, comonicon, dataframes, toml, algebraofgraphics, glm, statistics]
applies_when:
  - new julia development
  - adding dependencies
  - technology decisions
  - library selection
---

# ADR-001: Julia Technology Stack

## Status

Enforced

## Constraint (MUST)

This project MUST use the following Julia technology stack:

### Core Frameworks

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| **CLI Framework** | Comonicon | >=1.0.8 | Primary command-line interface framework |
| **CLI Alternative** | ArgParse | >=1.2.0 | Specific parsing needs (coexists with Comonicon) |
| **Data Processing** | DataFrames | >=1.7.0 | Primary data structure for wind data |
| **DataFrame Extensions** | DataFramesMeta | >=0.15.4 | Macro-based DataFrame transformations |
| **Statistical Modeling** | GLM | >=1.9.0 | Linear models for wind correlation |
| **Configuration** | TOML | >=1.0.3 | All configuration file formats |

### Visualization

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| **Visualization (Primary)** | AlgebraOfGraphics | >=0.10.7 | Grammar of graphics for wind plots |
| **Visualization Backend** | CairoMakie | >=0.13.7 | Rendering backend for AlgebraOfGraphics |
| **Color Schemes** | ColorSchemes | >=3.29.0 | Accessible color palettes |
| **Graphics** | Compose | >=0.9.6 | Vector graphics composition |

### I/O and Data Formats

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| **CSV Processing** | CSV | >=0.10.15 | Reading meteorological CSV files |
| **Data API** | DataAPI | >=1 | DataFrames interface compatibility |
| **Parquet Files** | Parquet2 | >=0.2 | Efficient columnar storage |
| **Julia Data Format** | JLD2 | >=0.5.11 | Native Julia data serialization |
| **JSON** | JSON | >=0.21.4 | Configuration and metadata exchange |
| **YAML** | YAML | >=0.4.12 | Alternative configuration format |

### Statistics and Mathematics

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| **Distributions** | Distributions | >=0.25.117 | Statistical distributions |
| **Statistics** | Statistics | >=1.11.1 | Standard library statistics |
| **StatsBase** | StatsBase | >=0.33.21 | Additional statistical functions |
| **Optimization** | Optim | >=1.11.0 | Optimization algorithms |
| **Clustering** | Clustering | *(no pin)* | Wind regime clustering |
| **Special Functions** | SpecialFunctions | >=2.5.0 | Mathematical special functions |

### Testing and Quality

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| **Testing Framework** | Test | >=1.11.0 | Julia standard testing |
| **Static Analysis** | JET | *(latest)* | Julia type inference analysis |
| **Static Linting** | StaticLint | >=8.2.2 | Code quality checks |

### Logging

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| **Logging (stdlib)** | Logging | >=1.11.0 | Standard library logging |
| **Logging Extras** | LoggingExtras | >=1.2.0 | Enhanced logging features |
| **Terminal Logging** | TerminalLoggers | >=0.1.7 | Terminal-specific log formatting |

### Other Dependencies

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| **Parameters** | Parameters | >=0.12.3 | Struct keyword constructors |
| **Word Documents** | WriteDocx | >=1.1.0 | Report generation |
| **Progress Meter** | ProgressMeter | >=1.10.4 | Long operation feedback |
| **Table Summaries** | SummaryTables | >=3.3.1 | Statistical table formatting |

### Standard Library

The following Julia standard library modules are used throughout:

- `Dates` - Timestamp handling
- `LinearAlgebra` - Vector operations for wind calculations
- `Printf` - Formatted output

## Rationale (WHY)

- **Comonicon**: Modern Julia CLI framework with automatic help generation, command discovery, and shell completion
- **ArgParse**: Coexists with Comonicon for specific argument parsing scenarios requiring fine-grained control
- **DataFrames/DataFramesMeta**: Industry standard for tabular data in Julia; DataFramesMeta enables functional transformation pipelines
- **GLM**: Mature, well-tested linear models for wind speed correlations and reconstruction algorithms
- **TOML**: Native Julia configuration format, aligns with Julia package structure (Project.toml)
- **AlgebraOfGraphics + CairoMakie**: Grammar of graphics approach enables consistent, maintainable wind data visualization
- **Parquet2**: Efficient storage for large wind time series datasets
- **JLD2**: Fast serialization for intermediate Julia data structures
- **JET**: Catches type instability at development time, critical for Julia performance

## Anti-Pattern (AVOID)

```julia
# ❌ WRONG: Using DataFrames without DataFramesMeta
using DataFrames  # ALWAYS include DataFramesMeta for transformations

# ❌ WRONG: Using Plots.jl instead of AlgebraOfGraphics
using Plots  # NEVER - use AlgebraOfGraphics + CairoMakie

# ❌ WRONG: Using JSON for configuration instead of TOML
# All configs MUST use TOML format

# ❌ WRONG: Using hardcoded column names instead of Symbol metadata
wind_speed = df[:, "wind_speed_80m"]  # Fragile!

# ✅ CORRECT: Using sensor metadata for column access
wind_speed = df[:, sensor.columnName]  # Use sensor metadata

# ❌ WRONG: Imperative loops with push! for data processing
results = Float64[]
for row in eachrow(df)
    if row.wind_speed > threshold
        push!(results, row.wind_speed)
    end
end

# ✅ CORRECT: Functional style with filter and broadcast
results = df[:, :wind_speed] |> speeds -> filter(s -> s > threshold, speeds)

# ❌ WRONG: Skipping type signatures
function process_wind_data(data, config)

# ✅ CORRECT: Restrictive type signatures
function process_wind_data(data::DataFrame, config::ProcessCleanConfig)::DataFrame
```

## Phase Links

Detailed guidance by workflow phase:

- **Plan**: [phases/stack-001-julia-tech-stack/on-plan.md](./phases/stack-001-julia-tech-stack/on-plan.md) - Stack selection guidance
- **Review Plan**: [phases/stack-001-julia-tech-stack/review-plan.md](./phases/stack-001-julia-tech-stack/review-plan.md) - Stack decision review
- **Code**: [phases/stack-001-julia-tech-stack/code.md](./phases/stack-001-julia-tech-stack/code.md) - Implementation patterns
- **Review Implementation**: [phases/stack-001-julia-tech-stack/review-implementation.md](./phases/stack-001-julia-tech-stack/review-implementation.md) - Compliance verification

## Validation

Quick compliance check:

```bash
# Check Project.toml exists and has required dependencies
test -f "CleanMastProject/Project.toml" || echo "FAIL: Missing Project.toml"

# Check core frameworks
grep -q 'Comonicon = "1.0.8"' CleanMastProject/Project.toml || echo "FAIL: Comonicon version mismatch"
grep -q 'DataFrames = "1.7.0"' CleanMastProject/Project.toml || echo "FAIL: DataFrames version mismatch"
grep -q 'TOML = "1.0.3"' CleanMastProject/Project.toml || echo "FAIL: TOML version mismatch"

# Check visualization stack
grep -q 'AlgebraOfGraphics = "0.10.7"' CleanMastProject/Project.toml || echo "FAIL: AlgebraOfGraphics version mismatch"
grep -q 'CairoMakie = "0.13.7"' CleanMastProject/Project.toml || echo "FAIL: CairoMakie version mismatch"

# Check data I/O
grep -q 'CSV = "0.10.15"' CleanMastProject/Project.toml || echo "FAIL: CSV version mismatch"
grep -q 'Parquet2 = "0.2"' CleanMastProject/Project.toml || echo "FAIL: Parquet2 version mismatch"

# Check statistics
grep -q 'GLM = "1.9.0"' CleanMastProject/Project.toml || echo "FAIL: GLM version mismatch"
grep -q 'Distributions = "0.25.117"' CleanMastProject/Project.toml || echo "FAIL: Distributions version mismatch"

# Check testing
grep -q 'Test = "1.11.0"' CleanMastProject/Project.toml || echo "FAIL: Test version mismatch"
```

## References

- [CleanMastProject/Project.toml](../../CleanMastProject/Project.toml) - Source of truth for dependency versions
- [CleanMastProject/AGENTS.md](../../CleanMastProject/AGENTS.md) - Coding standards and conventions
- Julia DataFrames documentation: https://dataframes.juliadata.org/
- AlgebraOfGraphics documentation: https://docs.makie.org/stable/explanations/backends/algebraofgraphics
- Comonicon documentation: https://comonicon.org/
