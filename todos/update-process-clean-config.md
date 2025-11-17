# TODO: Update ProcessCleanConfig to use from_dict/to_dict for Rules

## Context
Currently, `ProcessCleanConfig.Mast.rules` is defined as `Union{String, Array}` and the rules are loaded directly from the TOML without parsing into `Rule` objects. The actual parsing happens in `ProcessCleanCommand.jl` (lines 188-190).

## Current Approach
```julia
# In ProcessCleanConfig.jl
struct Mast
    name::String
    input::TimeSeriesSource
    output::TimeSeriesSource
    rules::Union{String,Array}  # <- Raw string or array
end

# In ProcessCleanCommand.jl
rules_config = mast_config.rules
rules_dict = isa(rules_config, String) ? load_dict(joinpath(project_dir, rules_config)) : rules_config
rules = [from_dict(Rule, r) for r in rules_dict["rules"]]
```

## Proposed Update
Update `ProcessCleanConfig` to follow the same pattern as `ReportCleanConfig`:

```julia
struct Mast
    name::String
    input::TimeSeriesSource
    output::TimeSeriesSource
    rules::Union{String, Vector{Rule}}  # <- Can be path or parsed rules
end
```

And add from_dict/to_dict implementations that handle both:
1. String path - load and parse the rules file
2. Inline array - parse rules directly

## Benefits
- Consistent approach across configurations
- Type safety with `Vector{Rule}` instead of raw `Array`
- Easier to work with rules programmatically
- Centralized rule parsing logic

## Files to Update
- `src/Types/ProcessCleanConfig.jl` - Add from_dict/to_dict for rules
- `src/DataClean/ProcessCleanCommand.jl` - Simplify rule loading
- Add proper imports for `Rule` and related types

## Related Work
This change was made for `ReportCleanConfig` in the layer difference table feature. See:
- `src/Types/ReportCleanConfig.jl` - Lines 32-44 (from_dict) and 79-144 (to_dict for Rule)
