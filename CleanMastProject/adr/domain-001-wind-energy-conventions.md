---
id: domain-001-wind-energy-conventions
name: wind-energy-conventions
description: Wind energy domain conventions for sensor types, stat types, data intervals, physical constraints, and the critical rule to use SensorColumn metadata instead of column name pattern matching
status: enforced
tags: [wind-energy, domain, sensors, mast, mesoscale, constraints]
applies_when:
  - working with sensor data
  - accessing DataFrame columns
  - filtering sensors
  - processing wind measurements
---

# ADR domain-001: Wind Energy Domain Conventions

## Status
Enforced

## Constraint (MUST)

### Sensor Types Priority
1. **Primary sensors MUST be prioritized for wind analysis:**
   - `WindSpeed` - wind speed measurements
   - `WindDirection` - wind direction measurements

2. **Secondary sensors MUST be used for environmental context:**
   - `Temperature` - air temperature
   - `Pressure` - atmospheric pressure
   - `Humidity` - relative humidity
   - `SolarRadiation` - solar radiation
   - `Precipitation` - precipitation

### Stat Type Priority
1. **`avg` (average) MUST be the primary statType for wind analysis**
2. **Secondary statTypes MAY be used for quality control:**
   - `std` - standard deviation
   - `min` - minimum value
   - `max` - maximum value

### Data Interval Conventions
1. **Mast data MUST use 10-minute averages as the standard interval**
2. **Mesoscale data MUST use 1-hour intervals for input**
3. **Timestamps MUST be validated and regularized to these intervals**

### Physical Constraints
1. **Wind speed MUST be in range 0-50 m/s**
2. **Wind direction MUST be in range 0-360 degrees**
3. **Temperature MUST use realistic ranges per sensor type**
4. **Pressure MUST use realistic ranges per sensor type**

### CRITICAL: Sensor Detection Rule (AVOID COLUMN NAME PATTERN MATCHING)
1. **NEVER scan column names to detect sensor types**
2. **ALWAYS use SensorColumn metadata from load_timeseries()**
3. **Column naming conventions vary across projects and processing stages**
4. **Using pattern matching causes missed sensors or wrong columns included**

### SensorColumn Metadata Access
1. **MUST access DataFrame columns via sensor.columnName (Julia Symbol)**
2. **MUST filter sensors using sensor.sensorType, sensor.statType, sensor.height**
3. **MUST use load_timeseries() to preserve sensor metadata**

## Rationale (WHY)

- **Primary vs secondary sensors**: WindSpeed and WindDirection are the core measurements for wind energy resource assessment. Other sensors provide context for data quality and environmental conditions.
- **avg statType**: Average values over the measurement interval represent the mean wind conditions, which is the standard for wind resource analysis.
- **10-minute mast intervals**: Industry standard for meteorological tower measurements, balancing temporal resolution with data volume.
- **1-hour mesoscale**: Mesoscale models typically output hourly data. Using consistent intervals simplifies data integration.
- **Physical constraints**: Realistic ranges enable data validation and outlier detection. Values outside these ranges indicate sensor errors.
- **SensorColumn metadata**: Column names change during preprocessing (merging, normalization, renaming). Only SensorColumn tracks the actual column name after all transformations. Pattern matching on column names is fragile and error-prone.

## Pattern (HOW)

### Loading Data with Sensor Metadata

```julia
# ✅ CORRECT: Use load_timeseries to preserve sensor metadata
source = TimeSeriesSource(data="./clean/M6002.parquet")
timeseries = load_timeseries(source, project_dir)

# Access the DataFrame
df = timeseries.df

# Access sensors with full metadata
sensors = timeseries.sensors  # Vector{SensorColumn}
```

### Filtering Sensors by Type

```julia
# ✅ CORRECT: Filter using sensor metadata
wind_speed_sensors = filter(
    s -> s.sensorType == "WindSpeed" && s.statType == "avg",
    sensors
)

# ✅ CORRECT: Find nearest height sensor
function find_wind_speed_sensor(sensors::Vector{SensorColumn}, height::Float64)
    return find_nearest_height_sensor(height, sensors, "WindSpeed", "avg")
end
```

### Accessing DataFrame Columns

```julia
# ✅ CORRECT: Use sensor.columnName (Symbol)
wind_speed_data = df[:, wind_speed_sensor.columnName]

# ✅ CORRECT: Check column existence
if hasproperty(df, sensor.columnName)
    data = df[:, sensor.columnName]
end
```

### Processing Wind Data

```julia
# ✅ CORRECT: Filter for primary sensors and avg statType
wind_sensors = filter(
    s -> s.sensorType in ["WindSpeed", "WindDirection"] && s.statType == "avg",
    sensors
)

# ✅ CORRECT: Validate physical constraints
valid_data = filter(
    row -> 0 <= row.wind_speed <= 50 && 0 <= row.wind_direction <= 360,
    df
)
```

### Sensor Short Name Convention

```julia
# ✅ CORRECT: Use standardized naming
sensor_name = create_sensor_short_name(sensor)
# Results: "WS:80m" or "WD:100m:N" or "WS:80m:std"
```

## Anti-Pattern (AVOID)

```julia
# ❌ WRONG: Pattern matching on column names (NEVER!)
ws_cols = [c for c in names(df) if startswith(c, "WS_")]  # NEVER!

# ❌ WRONG: Regex matching on column names (NEVER!)
wind_speed_cols = filter(
    c -> occursin(r"WindSpeed_\d+m", string(c)),
    names(df)
)  # NEVER!

# ❌ WRONG: Hardcoded column names
wind_speed = df[:, :wind_speed_80m]  # Fragile!

# ❌ WRONG: Using pl.read_parquet directly (loses metadata)
df = pl.read_parquet(path)  # Loses sensor metadata!

# ❌ WRONG: Assuming column naming conventions
col = "WindSpeed_100m_NE_avg [m/s]"  # Raw format
col = "WS_125m_fill:extrapolated"    # Processed format
# These vary across projects - NEVER rely on them!

# ❌ WRONG: Scanning column names for sensor types
def detect_wind_speed_columns(columns)
    wind_speed_cols = []
    for col in columns
        if match(r"WS_\d+m|WindSpeed_\d+m", col)  # NEVER!
            push!(wind_speed_cols, col)
        end
    end
    return wind_speed_cols
end

# ❌ WRONG: Filtering sensors without checking statType
wind_sensors = filter(s -> s.sensorType == "WindSpeed", sensors)
# Missing statType check - may include std/min/max when you want avg!

# ❌ WRONG: Using string column names with DataFrames
df[:, "wind_speed"]  # NEVER - use Symbol!
```

## Phase Links

| Phase | File | Purpose |
|-------|------|---------|
| **on-plan** | [phases/domain-001-wind-energy-conventions/on-plan.md](./phases/domain-001-wind-energy-conventions/on-plan.md) | Domain model design |
| **review-plan** | [phases/domain-001-wind-energy-conventions/review-plan.md](./phases/domain-001-wind-energy-conventions/review-plan.md) | Domain constraint review |
| **code** | [phases/domain-001-wind-energy-conventions/code.md](./phases/domain-001-wind-energy-conventions/code.md) | Sensor handling patterns |
| **review-implementation** | [phases/domain-001-wind-energy-conventions/review-implementation.md](./phases/domain-001-wind-energy-conventions/review-implementation.md) | Domain compliance verification |

## References

- SensorColumn struct: `CleanMastProject/src/Types/SensorColumns.jl`
- load_timeseries function: `CleanMastProject/src/ParseSensors/TimeSeriesLoad.jl`
- AGENTS.md domain section: Wind energy domain conventions
- Physical constraints: Range validation rules in `CleanMastProject/src/DataClean/ProcessRange.jl`
