---
id: config-001-toml-configuration
name: toml-configuration
description: TOML-based configuration system using Parameters.jl @with_kw structs for type-safe config loading
status: enforced
tags: [config, toml, parameters, settings, configuration-files]
applies_when:
  - adding new config types
  - loading configuration files
  - creating recommend commands
  - modifying config loading code
---

# ADR-001: TOML Configuration System

## Status

Enforced

## Constraint (MUST)

All configuration in this project MUST follow the TOML-based configuration pattern:

| Aspect | Requirement | Forbidden Alternatives |
|--------|-------------|----------------------|
| **Config Format** | TOML files (*.toml) | JSON, YAML, INI, XML |
| **Struct Definition** | `@with_kw` from Parameters.jl | Plain `struct`, `@kwdef` |
| **Config Loading** | `TOML.parsefile()` + struct unpacking | Manual field assignment |
| **File Naming** | `*Config.toml` or `{Module}.toml` | Generic names, no extension |
| **Config Generation** | `recommend` commands | Manual file creation |

All configuration structs MUST:
1. Be defined in `Types/` directory with `*Config.jl` suffix
2. Use `@with_kw` macro for keyword constructor
3. Provide a `load_*_config(configPath::String)` function
4. Support unpacking from TOML dict with `StructName(; dict...)`

## Rationale (WHY)

- **TOML**: Human-readable, supports comments, standard in Julia ecosystem
- **Parameters.jl @with_kw**: Provides keyword constructors, defaults, and unpacking syntax
- **Type-safe loading**: Config validation at load time via Julia type system
- **Consistent pattern**: Same loading pattern across all config types
- **Discoverable**: `recommend` commands generate valid starter configs

## Pattern (HOW)

### 1. Config Struct Definition

```julia
# Types/ProcessCleanConfig.jl
using Parameters: @with_kw

@with_kw struct ProcessCleanConfig
    rangeRules::Vector{RangeRule}
    layerDiffRules::Vector{LayerDiffRule}
    icingRules::Vector{IcingRule}
    availabilityRules::Vector{AvailabilityRule}
end
```

### 2. Config Loading Function

```julia
# Types/ProcessCleanConfig.jl
function load_process_clean_config(configPath::String)::ProcessCleanConfig
    configDict = TOML.parsefile(configPath)
    return ProcessCleanConfig(; configDict...)
end
```

### 3. Config File Example

```toml
# config/process-clean-config.toml
rangeRules = [
    {sensorType = "WindSpeed", minValue = 0.0, maxValue = 50.0},
    {sensorType = "WindDirection", minValue = 0.0, maxValue = 360.0}
]

layerDiffRules = [
    {sensorType = "WindSpeed", maxDiff = 5.0}
]

icingRules = [
    {temperatureThreshold = 2.0, windSpeedThreshold = 1.0}
]

availabilityRules = [
    {minAvailability = 0.9}
]
```

### 4. Recommend Command Pattern

```julia
# Command/RecommendProcessCleanCommand.jl
using Comonicon

@cast function recommend(outputPath::String)
    defaultConfig = ProcessCleanConfig(
        rangeRules = [
            RangeRule("WindSpeed", 0.0, 50.0),
            RangeRule("WindDirection", 0.0, 360.0)
        ],
        layerDiffRules = [LayerDiffRule("WindSpeed", 5.0)],
        icingRules = [IcingRule(2.0, 1.0)],
        availabilityRules = [AvailabilityRule(0.9)]
    )
    
    open(outputPath, "w") do io
        TOML.print(io, defaultConfig)
    end
end
```

### 5. Usage in Processing Commands

```julia
# Command/ProcessCleanCommand.jl
@cast function process(inputPath::String, configPath::String, outputPath::String)
    config = load_process_clean_config(configPath)
    data = load_timeseries(inputPath)
    
    # Apply range rules from config
    for rule in config.rangeRules
        apply_range_check(data, rule)
    end
    
    save_timeseries(outputPath, data)
end
```

## Anti-Pattern (AVOID)

```julia
# WRONG: Manual field access from dict
function load_config_bad(path::String)
    dict = TOML.parsefile(path)
    # Never manually extract fields - use struct unpacking
    return (
        rangeRules = dict["rangeRules"],
        layerDiffRules = dict["layerDiffRules"]
    )
end

# WRONG: Using @kwdef instead of @with_kw
@kwdef struct BadConfig  # Use @with_kw from Parameters.jl
    field::String
end

# WRONG: Plain struct without keyword constructor
struct BadConfig2  # Missing @with_kw
    field::String
end

# WRONG: Using JSON for configs
# configs should be *.toml, not *.json

# WRONG: Inline config without file
config = ProcessCleanConfig(...)  # Don't hardcode - use recommend command
```

## Phase Links

Detailed guidance by workflow phase:

- **Plan**: [phases/config-001-toml-configuration/on-plan.md](./phases/config-001-toml-configuration/on-plan.md) - Config design guidance
- **Review Plan**: [phases/config-001-toml-configuration/review-plan.md](./phases/config-001-toml-configuration/review-plan.md) - Config design review
- **Code**: [phases/config-001-toml-configuration/code.md](./phases/config-001-toml-configuration/code.md) - Config implementation patterns
- **Review Implementation**: [phases/config-001-toml-configuration/review-implementation.md](./phases/config-001-toml-configuration/review-implementation.md) - Compliance verification

## Validation

Quick compliance check:

```bash
# Check for TOML config files
find CleanMastProject -name "*.toml" -type f

# Verify Parameters.jl in dependencies
grep -q "Parameters" CleanMastProject/Project.toml || echo "FAIL: Parameters.jl missing"

# Check for @with_kw usage
grep -r "@with_kw" CleanMastProject/src/Types/ || echo "FAIL: No @with_kw found"

# Verify load_*_config functions exist
grep -r "function load_.*_config" CleanMastProject/src/ || echo "FAIL: No load_*_config functions"

# Check recommend commands
grep -r "recommend" CleanMastProject/src/Command/*.jl || echo "WARN: No recommend commands found"
```

## References

- [Parameters.jl Documentation](https://github.com/mauro3/Parameters.jl)
- [TOML.jl Standard Library](https://docs.julialang.org/en/v1/stdlib/TOML/)
- `CleanMastProject/src/Types/` - Config struct definitions
- `CleanMastProject/src/Command/Recommend*Command.jl` - Config generation commands
