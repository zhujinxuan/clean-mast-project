# process-clean.toml

## Structure

### [[masts]]

#### name
- Type: `String`
- Required: Yes
- Description: Mast identifier

#### input
- Type: `TimeSeriesSource`
- Required: Yes
- Description: Input data and sensors configuration
  - `data`: Path to input time series data (CSV or Parquet)
  - `sensors`: Path to sensors metadata file (TOML), optional for Parquet

#### output
- Type: `TimeSeriesSource`
- Required: Yes
- Description: Output data and sensors configuration
  - `data`: Output file path (CSV or Parquet)
  - `sensors`: Output sensors metadata file path

#### rules
- Type: `Union{String, Array}`
- Required: Yes
- Description: Cleaning rules configuration
  - If String: Path to rules file (TOML)
  - If Array: Inline rules configuration

### Rule Structure

#### name
- Type: `String`
- Required: Yes
- Description: Rule identifier

#### sensorType
- Type: `String`
- Required: Yes
- Description: Sensor type to apply rule to (e.g., "WindSpeed", "WindDirection")

#### height
- Type: `HeightFilter`
- Required: No
- Description: Height filter for rule application
  - `min`: Minimum height (optional)
  - `max`: Maximum height (optional)

#### criteria
- Type: `Union{RangeCriteria, LayerDifferenceCriteria, IcingCriteria, AvailabilityCriteria}`
- Required: Yes
- Description: Rule criteria (exactly one type required)

### RangeCriteria

#### min
- Type: `Union{Float64, Nothing}`
- Required: No
- Description: Minimum valid value

#### max
- Type: `Union{Float64, Nothing}`
- Required: No
- Description: Maximum valid value

### LayerDifferenceCriteria

#### lower_layer_height
- Type: `Float64`
- Required: Yes
- Description: Height of the lower reference layer in meters

#### abs_diff
- Type: `RangeCriteria`
- Required: Yes
- Description: Acceptable absolute difference range

#### lower_wind_speed
- Type: `RangeCriteria`
- Required: Yes
- Description: Wind speed range at lower layer for validation

### IcingCriteria

#### time_range
- Type: `Int64`
- Required: Yes
- Description: Time range in hours for icing detection

#### max_change
- Type: `Float64`
- Required: Yes
- Description: Maximum allowed change for icing detection

### AvailabilityCriteria

#### low_threshold
- Type: `Float64`
- Required: Yes
- Description: Low threshold for data availability check

## TODO: Usage Guidance (Stage 2)

- When to use this config
- Common patterns
- Recommended values
