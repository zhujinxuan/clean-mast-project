# wt-timeseries.toml

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

#### output_dir
- Type: `String`
- Required: Yes
- Description: Output directory for Meteodyn WT time series files

#### target_heights
- Type: `Vector{Float64}`
- Required: Yes
- Description: List of target heights for output wind turbine time series
  - Example: [80.0, 100.0, 120.0]

## TODO: Usage Guidance (Stage 2)

- When to use this config
- Common patterns
- Recommended values
