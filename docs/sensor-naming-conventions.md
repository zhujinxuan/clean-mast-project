# Sensor Naming Conventions for Reports

## Overview

This document establishes standardized sensor naming conventions for all report generation modules in the CleanMastProject system. These conventions ensure consistent and readable sensor identification across all generated reports.

## Naming Rules

All sensor names in reports shall follow these patterns:

### 1. For `statType = "avg"`

**With Direction:**
```
{sensorStyleShortName}:{height}m:{sensorDirection}
```

**Without Direction (when sensorDirection is "N/A"):**
```
{sensorStyleShortName}:{height}m
```

### 2. For Other `statType` Values

**With Direction:**
```
{sensorStyleShortName}:{height}m:{sensorDirection}:{statType}
```

**Without Direction (when sensorDirection is "N/A"):**
```
{sensorStyleShortName}:{height}m:{statType}
```

## Examples

### Average Statistics (statType = "avg")
- `WS:120m:N` - Wind speed sensor at 120m height, north orientation
- `WD:100m:N` - Wind direction sensor at 100m height, north orientation  
- `WS:80m` - Wind speed sensor at 80m height, no specific direction
- `TEMP:10m` - Temperature sensor at 10m height, no direction specified

### Non-Average Statistics
- `WS:120m:N:max` - Maximum wind speed sensor at 120m height, north orientation
- `WS:120m:N:min` - Minimum wind speed sensor at 120m height, north orientation
- `WS:80m:std` - Wind speed standard deviation sensor at 80m height, no direction
- `GUST:100m:max` - Maximum gust sensor at 100m height, no direction

## Component Definitions

- **`sensorStyleShortName`**: Short identifier for sensor type (e.g., WS, WD, TEMP, GUST)
- **`height`**: Sensor height in meters
- **`sensorDirection`**: Physical orientation of sensor (N, S, E, W, NE, etc.) or "N/A" when no specific direction applies
- **`statType`**: Statistical measurement type (avg, max, min, std, etc.)

## Implementation Notes

### Current State
- **Data coverage reports** may not currently follow this convention
- This standardization will be applied to new report generation modules first
- Existing reports will be updated in future modifications

### Future Work
- Update existing report modules to use these conventions
- Implement automatic sensor name formatting functions
- Ensure consistency across all report types

## Usage Guidelines

### When to Apply
- All new report generation modules must use these conventions
- Any modifications to existing reports should adopt these standards
- Cross-references between reports should use consistent naming

### Quality Assurance
- Sensor names should be validated against these patterns
- Reports should include clear legends explaining abbreviations
- Direction indicators should be consistent with measurement metadata

## Related Documents

- [Tower Shading Analysis](tower-shading.md) - Related sensor processing workflow
- [Representative Year Analysis](representative-year.md) - Example usage context
- [Data Coverage Reports](process-clean.md) - Current implementation to be updated

## Validation Examples

✅ **Correct Examples:**
- `WS:140m:N`
- `WD:120m`  
- `TEMP:10m:max`
- `WS:80m:E:std`

❌ **Incorrect Examples:**
- `WindSpeed_140m_North` (wrong format)
- `WS-140-N` (wrong separators)
- `WS:140:N:avg` (unnecessary avg for average sensors)
- `WS::140m:N` (missing height)

This naming convention ensures that all sensors are clearly identified with their key characteristics while maintaining readability and consistency across the entire reporting system.