---
id: data-003-parquet-format
name: parquet-format
description: Parquet file format for time series data storage using Parquet2.jl. Metadata stored at file level as JSON, not column level. Auto-detection by .parquet extension.
status: enforced
tags: [julia, parquet, data-storage, timeseries, metadata]
applies_when:
  - writing time series data to disk
  - reading time series data from disk
  - storing sensor metadata with data files
  - implementing data persistence
---

# ADR-003: Parquet Format for Time Series Data

## Status
**Enforced**

## Constraint (MUST)

1. **MUST use Parquet2.jl library for Parquet operations**
2. **MUST store sensor metadata at FILE level, NOT column level**
3. **MUST use `Parquet2.writefile()` with metadata Dict parameter**
4. **MUST use `Parquet2.Dataset(path)` for reading**
5. **MUST auto-detect format by file extension (.parquet vs .csv)**
6. **MUST serialize sensor metadata as JSON string**

## Rationale (WHY)

- **Parquet2.jl**: Native Julia implementation with better integration than alternatives, supporting both writing and reading operations efficiently.
- **File-level metadata**: The actual implementation in MastTimeSeries.jl uses file-level metadata (`metadata=Dict{String, String}`) to store sensor information. This is the verified pattern.
- **JSON serialization**: Sensor metadata is complex structured data. JSON provides a standard, readable format that can be parsed back when loading.
- **Auto-detection**: Using file extension allows seamless switching between CSV and Parquet formats without code changes.
- **Dataset API**: `Parquet2.Dataset` provides lazy loading and efficient column access for large time series files.

## Pattern (HOW)

### Writing Parquet Files with Metadata

```julia
using Parquet2
using JSON

# ✅ CORRECT: Write DataFrame with file-level metadata
sensors_dict = Dict(
    "sensors" => [
        Dict("columnName" => "ws_80m", "type" => "WindSpeed", "height" => 80),
        Dict("columnName" => "wd_80m", "type" => "WindDirection", "height" => 80)
    ]
)
sensors_json = JSON.json(sensors_dict)

Parquet2.writefile(
    output_path,
    df;
    metadata=Dict{String, String}("cleanmast_sensors" => sensors_json)
)
```

### Reading Parquet Files

```julia
using Parquet2

# ✅ CORRECT: Load as Dataset for efficient access
ds = Parquet2.Dataset(source.data)

# ✅ CORRECT: Convert to DataFrame when needed
df = DataFrame(ds)
```

### Format Auto-Detection

```julia
# ✅ CORRECT: Detect format by extension
function load_timeseries(path::String)
    if endswith(lowercase(path), ".parquet")
        ds = Parquet2.Dataset(path)
        return DataFrame(ds)
    else
        return CSV.read(path, DataFrame)
    end
end
```

### Sensor Metadata Storage

```julia
# ✅ CORRECT: TimeSeriesSource with optional sensors field
mutable struct TimeSeriesSource
    data::String           # Path to data file
    sensors::Union{String, Nothing}  # JSON string or nothing
end

# ✅ CORRECT: Serialize sensor array to JSON
function serialize_sensors(sensors::Vector{SensorColumn})
    sensor_dicts = [
        Dict(
            "columnName" => s.columnName,
            "type" => string(s.type),
            "height" => s.height,
            "orientation" => s.orientation
        ) for s in sensors
    ]
    return JSON.json(Dict("sensors" => sensor_dicts))
end
```

### Loading with Metadata

```julia
# ✅ CORRECT: Read metadata from parquet file
function load_with_metadata(path::String)
    ds = Parquet2.Dataset(path)
    df = DataFrame(ds)
    
    # Access file-level metadata
    if haskey(ds.metadata, "cleanmast_sensors")
        sensors_json = ds.metadata["cleanmast_sensors"]
        sensors_data = JSON.parse(sensors_json)
        return df, sensors_data["sensors"]
    end
    
    return df, nothing
end
```

## Anti-Pattern (AVOID)

```julia
# ❌ WRONG: Using column-level metadata (NOT how code works)
Parquet2.writefile(
    path, df;
    column_metadata=Dict(...)  # NEVER - use file-level metadata
)

# ❌ WRONG: Using pyarrow (Python library, not Julia)
using PyCall  # NEVER for parquet in Julia code
pyarrow = pyimport("pyarrow")

# ❌ WRONG: Storing metadata as binary or non-JSON format
metadata=Dict("sensors" => string(sensors))  # NEVER - use JSON

# ❌ WRONG: Using Parquet2.File instead of Dataset for reading
pf = Parquet2.File(path)  # AVOID - use Dataset for time series

# ❌ WRONG: File extension check without lowercase
if endswith(path, ".parquet")  # RISKY - use lowercase()

# ❌ WRONG: Missing type annotation on metadata Dict
metadata=Dict("key" => value)  # AVOID - use Dict{String, String}
```

## Phase Links

This ADR uses **phase-based documentation**. Load the appropriate phase file for your role:

| Phase | File | When to Load |
|-------|------|--------------|
| **on-plan** | [`phases/data-003-parquet-format/on-plan.md`](phases/data-003-parquet-format/on-plan.md) | Designer: Data persistence design |
| **review-plan** | [`phases/data-003-parquet-format/review-plan.md`](phases/data-003-parquet-format/review-plan.md) | Reviewer: Validating storage designs |
| **code** | [`phases/data-003-parquet-format/code.md`](phases/data-003-parquet-format/code.md) | Coder: Implementation |
| **review-implementation** | [`phases/data-003-parquet-format/review-implementation.md`](phases/data-003-parquet-format/review-implementation.md) | Reviewer: Code review |

### Quick Compliance Check

```bash
# Validate ADR-003 compliance - check for correct Parquet2 usage
grep -rn 'Parquet2.writefile' src/ && echo "OK: Parquet2.writefile found"
grep -rn 'Parquet2.Dataset' src/ && echo "OK: Parquet2.Dataset found"

# Check for anti-patterns
grep -rn 'pyarrow' src/ && echo "WARNING: pyarrow found (should use Parquet2.jl)"
grep -rn 'column_metadata' src/ && echo "WARNING: column_metadata found (use file-level)"
```

## References

- [MastTimeSeries.jl](../src/Types/MastTimeSeries.jl) - Parquet reading/writing implementation
- [Project.toml](../Project.toml) - Parquet2.jl dependency
- Parquet2.jl documentation: https://github.com/JuliaIO/Parquet.jl
- JSON.jl documentation: https://github.com/JuliaIO/JSON.jl
