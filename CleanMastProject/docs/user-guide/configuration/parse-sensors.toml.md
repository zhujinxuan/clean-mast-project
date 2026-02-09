# parse-sensors.toml

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
  - `data`: Path to raw data file (CSV)
  - `sensors`: Path to sensors metadata file (TOML), optional for Parquet format

#### sensor
- Type: `Union{String, SensorFormatConfig}`
- Required: Yes
- Description: Sensor column configuration
  - If String: Path to sensor format config file
  - If Object: Inline sensor format configuration

#### output
- Type: `TimeSeriesSource`
- Required: Yes
- Description: Output data and sensors configuration
  - `data`: Output file path (CSV or Parquet)
  - `sensors`: Output sensors metadata file path

#### interpolate
- Type: `Union{InterpolationConfig, Nothing}`
- Required: No
- Description: Time series interpolation configuration

### [[mesos]]

Same structure as `[[masts]]`.

### InterpolationConfig

#### from_minutes
- Type: `Int`
- Required: Yes
- Description: Source interval in minutes

#### to_minutes
- Type: `Int`
- Required: Yes
- Description: Target interval in minutes

### SensorFormatConfig

#### columns
- Type: `Vector{SensorColumnConfig}`
- Required: No
- Description: Column parsing configurations

#### timestamp_column
- Type: `String`
- Required: Yes
- Description: Name of timestamp column

#### timestamp_format
- Type: `Union{String, Nothing}`
- Required: No
- Description: Optional timestamp format string

#### delim
- Type: `Union{String, Nothing}`
- Required: No
- Description: Optional delimiter for CSV parsing

#### skip_to
- Type: `Union{Int64, Nothing}`
- Required: No
- Description: Optional number of lines to skip

#### mappings
- Type: `Vector{MappingRule}`
- Required: No
- Description: Mapping rules for sensor transformation

### SensorColumnConfig

#### match
- Type: `String`
- Required: Yes
- Description: Pattern for extracting data from column names

#### format
- Type: `String`
- Required: Yes
- Description: Pattern for normalizing column names

#### patterns
- Type: `Union{PatternConfig, Nothing}`
- Required: No
- Description: Optional regex patterns for placeholders

### MappingRule

#### match
- Type: `Dict{String, Union{Nothing, Float64, String}}`
- Required: Yes
- Description: Matching criteria for sensor identification

#### rule
- Type: `RuleOutcome`
- Required: Yes
- Description: Sensor metadata to apply when matched

### RuleOutcome

#### sensorType
- Type: `Union{String, Nothing}`
- Required: No
- Description: Sensor type (e.g., "WindSpeed", "WindDirection")

#### sensorDirection
- Type: `Union{String, Nothing}`
- Required: No
- Description: Sensor direction (e.g., "N", "S", "N/A")

#### height
- Type: `Union{Float64, Nothing}`
- Required: No
- Description: Sensor height in meters

#### statType
- Type: `Union{String, Nothing}`
- Required: No
- Description: Statistic type (e.g., "avg", "max", "min")

#### unit
- Type: `Union{String, Nothing}`
- Required: No
- Description: Unit of measurement

#### multiplier
- Type: `Union{Float64, Nothing}`
- Required: No
- Description: Conversion multiplier

### PatternConfig

#### patterns
- Type: `Dict{String, String}`
- Required: Yes
- Description: Placeholder name to regex pattern mapping

## TODO: Usage Guidance (Stage 2)

- When to use this config
- Common patterns
- Recommended values
