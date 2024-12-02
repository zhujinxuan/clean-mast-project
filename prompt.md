# CleanMast

CleanMast is a Julia project for processing wind mast data, specifically designed to parse, clean, and reconstruct data from mast tower CSV files.

## Project Structure

```
CleanMast/
├── src/
│   ├── CleanMast.jl           # Main entry point
│   ├── CleanMastConfig.jl     # Configuration handling
│   ├── MastTimeSeries.jl      # Data processing and parsing
│   └── CleanMastRules/        # Data cleaning rules
│       ├── Rules.jl           # Rule definitions
│       ├── ProcessTypes.jl    # Common types for processing
│       ├── ProcessRange.jl    # Range validation
│       ├── ProcessIcing.jl    # Icing detection
│       ├── ProcessLayerDiff.jl # Layer difference checks
│       └── Process.jl         # Main processing entry
├── test/
│   ├── runtests.jl
│   ├── test_parsing.jl
│   └── test_rules.jl
└── config/
    ├── config.yaml           # Project configuration
    └── rules.yaml           # Rule definitions
```

## Configuration

### Project Configuration (config.yaml)
```yaml
Mast:
  data_path: data.csv  # Path to data file (relative to config.yaml)
  skip_to: 0          # Number of rows to skip in CSV
  sensor:
    column_format: "Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}"
    timestamp_column: Timestamp
    timestamp_format: "yyyy-MM-dd HH:mm"
    mappings:
      sensor_types:
        Anem: WindSpeed
        Vane: WindDirection
      stat_types:
        Avg: avg
        Max: max
        Min: min
        SD: sd
      units:
        m/s: speed
        Deg: degrees
  rules:
    - name: "High Wind Speed Layer Difference"
      sensorType: "WindSpeed"
      height:
        min: 70.0
        max: null
      layer_difference:
        lower_layer_height: 20.0
        abs_diff:
          min: null
          max: 2.0
        lower_wind_speed:
          min: null
          max: null
    - name: "High Wind Speed Layer Difference"
      sensorType: "WindDirection"
      height:
        min: 70.0
        max: null
      layer_difference:
        lower_layer_height: 20.0
        abs_diff:
          min: null
          max: 22.5
        lower_wind_speed:
          min: 3
          max: 25
    - name: "Wind Speed Range"
      sensorType: "WindSpeed"
      height:
        min: null
        max: null
      out_of_range:
        min: 0.0
        max: 30.0
    - name: "Wind Direction Range"
      sensorType: "WindDirection"
      height:
        min: null
        max: null
      out_of_range:
        min: 0.0
        max: 360.0
    - name: "Icing WS Detection"
      sensorType: "WindSpeed"
      height:
        min: null
        max: null
      icing:
        time_range: 7200
        max_change: 0.02
```

### Commonly needed Types

Here TimeSeriesData is reading the mast time series and parse all sensors. All data cleaning and 
```julia
struct SensorColumn
    columnName::Symbol     # df Symbol corresponding to the sensor
    sensorType::String      # "WindSpeed" | "WindDirection" | "Temperature" | "Pressure"
    sensorDirection::String # Could be converted to Float64 later if needed
    height::Float64
    statType::String       # "avg" | "max" | "min" | "sd"
end

struct TimeSeriesData
    df::DataFrame # where mast data csv stores, with timestamp by default as 
    sensors::Vector{SensorColumn}
end
```


### Rule Configuration (rules.yaml)
```yaml
```

## Rule Types

Each rule must have exactly one of:
1. `out_of_range`: Value range validation
2. `layer_difference`: Compare measurements between layers
3. `icing`: Detect constant values over time

### Layer Difference Rules
- Supports both wind speed and direction comparisons
- Uses closest available wind speed measurement within 10m height difference
- For wind direction, handles circular difference calculation

### Icing Detection
- Checks for minimal variation over specified time period
- Duration specified in seconds
- Supports different thresholds per height

### Range Validation
- Simple min/max bounds checking
- Can be height-specific
- Handles missing values

## Development Status
- ✅ Configuration parsing 
- ✅ Column name parsing with flexible format
- ✅ Basic data reading with type handling
- ✅ Sensor metadata generation
- [ ] Post metadata generation to diff Temperature and Pressure
- ✅ Command line interface
- ✅ Rule definition and loading
- ✅ Rule processing implementation
- ✅ Test coverage for rules
- [ ] More detailed test for data cleaning rule
- [ ] Tower shading adjustment
- [ ] Reconstruct data within the mast data
- [ ] Reconstruct data from mesoscale data
- [ ] Performance optimization
- [ ] Output formatting options

## Code Standards
- Functional programming style preferred
- Type specifications required
- Unit tests for data cleaning and data reconstructing
- Use docstrings for functions and types
