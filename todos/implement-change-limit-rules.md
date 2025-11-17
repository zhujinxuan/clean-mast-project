# Implement Change Limit Validation Rules

## Purpose

Implement missing data quality validation rules from Chinese standard 表 2.3.2-3 (Table 2.3.2-3) for detecting abnormal sensor value changes over time.

## Background

Currently, the CleanMast system implements several data quality rules:
- `RangeCriteria` - value range validation
- `LayerDifferenceCriteria` - inter-sensor layer difference checks
- `IcingCriteria` - sensor freezing detection (constant values over time)
- `AvailabilityCriteria` - data availability thresholds

However, the following validation rules from 表 2.3.2-3 are **not yet implemented**:

| 主要参数 | 参考范围 |
|---------|---------|
| 1小时平均气温变化 | -5℃ ~ 5℃ |
| 3小时平均气压变化 | 1kPa ~<1kPa |
| 风速连续无变化持续时间 | 小于2h |
| 风向连续无变化持续时间 | 非静风条件下小于2h |

## Proposed Implementation

### 1. Add New Criteria Type

Following the existing pattern in `src/Types/CleanRules.jl`, add a new `ChangeCriteria` struct:

```julia
struct ChangeCriteria
    duration_seconds::Int64      # Time window for change calculation (e.g., 3600, 10800)
    change_range::RangeCriteria  # Allowable change range (min, max)
end
```

This follows the same design pattern as `IcingCriteria`:
- `sensorType` is already in the `Rule` struct, so the same criteria can be reused for Temperature, Pressure, WindSpeed, WindDirection
- `duration_seconds` specifies the time window (1 hour = 3600s, 3 hours = 10800s)
- `change_range` uses existing `RangeCriteria` for min/max validation

### 2. Update Rule Union Type

In `src/Types/CleanRules.jl`, update the `Rule` struct:

```julia
struct Rule
    name::String
    sensorType::String
    height::HeightFilter
    criteria::Union{RangeCriteria, LayerDifferenceCriteria, IcingCriteria, AvailabilityCriteria, ManualCriteria, ChangeCriteria}
end
```

### 3. Update from_dict Function

Add parsing logic in the `from_dict(::Type{Rule}, config::Dict{String, Any})` function:

```julia
function from_dict(::Type{Rule}, config::Dict{String, Any})::Rule
    # Update criteria_keys list
    criteria_keys = ["out_of_range", "layer_difference", "icing", "availability", "change"]

    # ... existing validation ...

    elseif haskey(config, "change")
        ch = config["change"]
        criteria = ChangeCriteria(
            ch["duration_seconds"],
            RangeCriteria(
                get(ch["change_range"], "min", nothing),
                get(ch["change_range"], "max", nothing)
            )
        )
    end

    # ... rest of function ...
end
```

### 4. Implement Validation Logic

Create validation function in `src/DataClean/` (similar to existing icing detection):

```julia
function validate_change_criteria(
    data::DataFrame,
    sensor::SensorColumn,
    criteria::ChangeCriteria,
    timestamps::Vector{DateTime}
)::Vector{Bool}
    # Calculate rolling changes over duration_seconds window
    # Compare against change_range.min and change_range.max
    # Return violation flags for each timestamp
end
```

### 5. TOML Configuration Examples

#### Temperature Change Validation
```toml
[[rules]]
name = "1-hour Temperature Change"
sensorType = "Temperature"
[rules.change]
duration_seconds = 3600
[rules.change.change_range]
min = -5.0
max = 5.0
```

#### Pressure Change Validation
```toml
[[rules]]
name = "3-hour Pressure Change"
sensorType = "Pressure"
[rules.change]
duration_seconds = 10800
[rules.change.change_range]
min = -1.0  # or handle the asymmetric range appropriately
max = 1.0
```

#### Wind Speed No-Change Detection
```toml
[[rules]]
name = "Wind Speed Continuous No-Change"
sensorType = "WindSpeed"
[rules.change]
duration_seconds = 7200  # 2 hours
[rules.change.change_range]
min = 0.001  # Require at least minimal change
max = 999.0
```

Note: This overlaps with existing `IcingCriteria` functionality. Consider whether to:
- Keep both (change criteria more general, icing criteria specific)
- Migrate icing detection to use change criteria
- Use change criteria for different validation scenarios

## Implementation Checklist

- [ ] Add `ChangeCriteria` struct to `src/Types/CleanRules.jl`
- [ ] Update `Rule.criteria` union type to include `ChangeCriteria`
- [ ] Add `"change"` to `criteria_keys` in `from_dict` function
- [ ] Implement parsing logic for `ChangeCriteria` in `from_dict`
- [ ] Export `ChangeCriteria` in module exports
- [ ] Implement `validate_change_criteria` function in `src/DataClean/`
- [ ] Integrate change validation into main data cleaning pipeline
- [ ] Add tests for change criteria parsing and validation
- [ ] Update `example_project/formats/clean/default.toml` with example rules
- [ ] Document the new criteria type in user documentation

## Notes

### Relationship to IcingCriteria

The existing `IcingCriteria` detects sensor freezing (constant values):
```julia
struct IcingCriteria
    time_range::Int64
    max_change::Float64
end
```

The new `ChangeCriteria` is more general and can detect:
- **Excessive changes** (temperature/pressure jumps)
- **Insufficient changes** (no-change detection, similar to icing)

Consider whether to:
1. Keep both criteria types for different use cases
2. Deprecate `IcingCriteria` in favor of `ChangeCriteria`
3. Use `ChangeCriteria` for temperature/pressure, keep `IcingCriteria` for wind sensors

### Asymmetric Ranges

The standard specifies "1kPa ~<1kPa" for pressure change, which suggests:
- Increases up to 1kPa are acceptable
- Decreases should be less than 1kPa (but how much less?)

This may require clarification or a different configuration format if the range is truly asymmetric.

### Wind Direction No-Change Under Non-Calm Conditions

The standard specifies "非静风条件下小于2h" (less than 2h under non-calm conditions).

This requires conditional logic:
- Only apply the rule when wind speed > threshold (e.g., 3 m/s)
- Skip validation during calm wind periods

This may require additional fields in `ChangeCriteria` or special handling in validation logic.

## References

- Chinese standard: 表 2.3.2-3 主要参数合理变化趋势参考值表
- Existing implementation: `src/Types/CleanRules.jl`
- Icing detection: `src/DataClean/` (search for IcingCriteria usage)
- Configuration example: `example_project/formats/clean/default.toml`
