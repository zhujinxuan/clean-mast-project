# CleanMast

CleanMast is a Julia project for processing wind mast data, specifically designed to parse, clean, and analyze data from meteodyn mast CSV files.

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
        Analog: Temperature
      stat_types:
        Avg: avg
        Max: max
        Min: min
        SD: sd
      units:
        m/s: speed
        Deg: degrees
        C: celsius
```

### Rule Configuration (rules.yaml)
```yaml
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

  - name: "Wind Speed Range"
    sensorType: "WindSpeed"
    height:
      min: null
      max: null
    out_of_range:
      min: 0.0
      max: 50.0

  - name: "Icing Detection"
    sensorType: "WindSpeed"
    height:
      min: null
      max: null
    icing:
      time_range: 7200
      max_change: 0.02
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
- ✅ Command line interface
- ✅ Rule definition and loading
- ✅ Rule processing implementation
- ✅ Test coverage for rules
- [ ] Performance optimization
- [ ] Output formatting options

## Code Standards
- Functional programming style preferred
- Type specifications required
- Unit tests for each rule type
- Use docstrings for functions and types
