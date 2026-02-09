# train-meso.toml

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
  - `data`: Path to mast time series data (CSV or Parquet)
  - `sensors`: Path to sensors metadata file (TOML), optional for Parquet

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

### [[models]]

#### mast_name
- Type: `String`
- Required: Yes
- Description: Name of the mast to train model for

#### meso_name
- Type: `String`
- Required: Yes
- Description: Name of the mesoscale source to correlate with

#### method
- Type: `String`
- Required: Yes
- Description: Correlation method
  - Values: "16-sector", "1-sector", "constant-direction-offset"

#### output
- Type: `String`
- Required: Yes
- Description: Path to output model file (.jld2)

## TODO: Usage Guidance (Stage 2)

- When to use this config
- Common patterns
- Recommended values
