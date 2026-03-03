---
id: types-001-julia-type-system
name: julia-type-system
description: Julia type system patterns for structs, function signatures, abstract types, and config loading with strict type annotations
status: enforced
tags: [julia, types, structs, parameters, abstract-types, functions, config]
applies_when:
  - writing julia code
  - defining structs
  - function signatures
  - type annotations
  - config loading
---

# ADR types-001: Julia Type System Patterns

## Status
Enforced

## Constraint (MUST)

1. **ALL struct fields MUST have explicit type annotations**
2. **ALL function parameters MUST have type annotations**
3. **ALL function return types MUST be declared**
4. **Use `Union{Type, Missing}` for nullable fields** (not `Union{Missing, Type}`)
5. **Use `@with_kw` from Parameters.jl for config structs** with keyword constructors
6. **Define abstract type hierarchies with `<:` syntax** for extensible models
7. **Use `Symbol` type for DataFrame column references**
8. **Config loading MUST use TOML.parsefile with splatting**

## Rationale (WHY)

- **Explicit types**: Julia's multiple dispatch relies on type specificity for performance and correctness
- **Return type annotations**: Enables compiler optimizations and catches errors at function boundaries
- **`@with_kw`**: Simplifies config creation with default values and keyword arguments
- **Abstract types**: Enable polymorphism and extensible design patterns
- **Union ordering**: Consistency with Julia convention (concrete type first)

## Pattern (HOW)

### Struct Definition with Type Annotations

```julia
@with_kw struct SensorColumn
    columnName::Symbol
    sensorType::String
    sensorDirection::String
    height::Float64
    statType::String
    unit::String
end
```

### Config Struct with Parameters.jl

```julia
using Parameters

@with_kw struct ProcessCleanConfig
    rangeRules::Vector{RangeRule}
    layerDiffRules::Vector{LayerDiffRule}
    icingRules::Vector{IcingRule}
    availabilityRules::Vector{AvailabilityRule}
end
```

### Abstract Type Hierarchy

```julia
abstract type MastReferenceModel end
abstract type WindSpeedModel <: MastReferenceModel end
abstract type WindDirectionModel <: MastReferenceModel end
```

### Function with Complete Type Annotations

```julia
function process_range(
    df::DataFrame,
    sensor::SensorColumn,
    minVal::Union{Float64, Missing},
    maxVal::Union{Float64, Missing}
)::Tuple{DataFrame, Vector{ViolationData}}
    # implementation
end
```

### Config Loading Pattern

```julia
function load_process_clean_config(configPath::String)::ProcessCleanConfig
    configDict = TOML.parsefile(configPath)
    return ProcessCleanConfig(; configDict...)
end
```

## Anti-Pattern (AVOID)

```julia
# ❌ WRONG: Untyped struct fields
struct BadSensor
    columnName  # No type annotation
    height      # Missing Union with Missing
end

# ❌ WRONG: Untyped function parameters
function process_data(df, sensor, minVal)  # No types
    # ...
end

# ❌ WRONG: Missing return type
function load_config(path::String)  # No return type
    # ...
end

# ❌ WRONG: Union ordering (Missing first)
height::Union{Missing, Float64}  # ❌ Use Union{Float64, Missing}

# ❌ WRONG: String column references for DataFrames
function get_data(df::DataFrame, col::String)  # Use Symbol instead
    df[:, col]
end

# CORRECT:
function get_data(df::DataFrame, col::Symbol)::Vector{Float64}
    df[:, col]
end
```

## Phase Links

| Phase | File | Purpose |
|-------|------|---------|
| **on-plan** | [phases/types-001-julia-type-system/on-plan.md](./phases/types-001-julia-type-system/on-plan.md) | Type design for domain models |
| **review-plan** | [phases/types-001-julia-type-system/review-plan.md](./phases/types-001-julia-type-system/review-plan.md) | Type design review checklist |
| **code** | [phases/types-001-julia-type-system/code.md](./phases/types-001-julia-type-system/code.md) | Function signatures, type annotations |
| **review-implementation** | [phases/types-001-julia-type-system/review-implementation.md](./phases/types-001-julia-type-system/review-implementation.md) | Type compliance verification |

## References

- [Julia Documentation - Types](https://docs.julialang.org/en/v1/manual/types/)
- [Parameters.jl Documentation](https://github.com/mauro3/Parameters.jl)
- [Julia Multiple Dispatch](https://docs.julialang.org/en/v1/manual/methods/)
- Source files: `CleanMastProject/src/Types/SensorColumns.jl`, `CleanMastProject/src/Types/ViolationData.jl`, `CleanMastProject/src/Types/ProcessCleanConfig.jl`
