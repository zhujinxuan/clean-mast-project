# reconstruct-meso.toml

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

#### time_range
- Type: `TimeRange`
- Required: Yes
- Description: Time range for reconstruction
  - `min`: Start datetime
  - `max`: End datetime

#### models
- Type: `ReconstructMesoModels`
- Required: Yes
- Description: Mesoscale model specifications

### [[mesos]]

#### name
- Type: `String`
- Required: Yes
- Description: Mesoscale data source identifier

#### input
- Type: `TimeSeriesSource`
- Required: Yes
- Description: Input data and sensors configuration
  - `data`: Path to mesoscale time series data (CSV or Parquet)
  - `sensors`: Path to sensors metadata file (TOML), optional for Parquet

### ReconstructMesoModels

#### windspeed
- Type: `ReconstructMesoModelSpec`
- Required: Yes
- Description: Wind speed reconstruction model specification

#### winddirection
- Type: `ReconstructMesoModelSpec`
- Required: Yes
- Description: Wind direction reconstruction model specification

### ReconstructMesoModelSpec

#### method
- Type: `String`
- Required: Yes
- Description: Correlation method
  - Values: "16-sector", "1-sector", "constant-direction-offset"

#### meso_name
- Type: `String`
- Required: Yes
- Description: Name of the mesoscale source

#### model_file
- Type: `String`
- Required: Yes
- Description: Path to trained model file (.jld2)

## TODO: Usage Guidance (Stage 2)

- When to use this config
- Common patterns
- Recommended values
