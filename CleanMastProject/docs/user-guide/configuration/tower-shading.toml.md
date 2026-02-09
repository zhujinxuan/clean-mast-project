# tower-shading.toml

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

## TODO: Usage Guidance (Stage 2)

- When to use this config
- Common patterns
- Recommended values
