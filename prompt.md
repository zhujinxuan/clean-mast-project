Here's a comprehensive README for the CleanMast project:

```markdown
# CleanMast

CleanMast is a Julia project for processing wind mast data, specifically designed to parse, clean, and analyze data from meteodyn mast CSV files. The project uses configuration-driven approach for flexible data processing and validation.

## Project Structure

```
CleanMast/
├── src/
│   ├── CleanMast.jl         # Main entry point, command line interface
│   ├── CleanMastConfig.jl   # Configuration handling
│   └── MastTimeSeries.jl    # Data processing and parsing
├── test/
│   ├── runtests.jl          # Test entry point
│   └── test_parsing.jl      # Tests for parsing functionality
└── config.yaml              # Example configuration file
```

## Usage

### Command Line Interface

The project provides a command-line interface with the following commands:

```bash
# Check configuration file
julia ./src/CleanMast.jl check:config --dir=<project_dir>

# Parse mast data and generate sensors metadata
julia ./src/CleanMast.jl check:sensors --dir=<project_dir>
```

### Configuration

Create a `config.yaml` in your project directory:

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

## Development Status

Current implementation includes:
- ✅ Configuration parsing (CleanMastConfig)
- ✅ Column name parsing with flexible format
- ✅ Basic data reading with type handling
- ✅ Sensor metadata generation
- ✅ Command line interface
- ✅ Unit tests for parsing

Next steps:
- [ ] Data cleaning rules implementation
- [ ] Data validation
- [ ] Time series analysis functions
- [ ] Output formatting options
- [ ] Additional data processing features

## Code Standards

### Naming Conventions
- Use PascalCase for types and modules (e.g., `SensorConfig`, `MastTimeSeries`)
- Use lowercase with underscores for filenames (e.g., `clean_mast.jl`)
- Use camelCase for variable and function names (e.g., `parseConfig`, `sensorType`)

### Type and Function Specifications
- Always specify types for struct fields
- Use type annotations for function arguments and return values
- Use docstrings for functions and types

Example:
```julia
"""
Parse a single column name based on format pattern.
Returns nothing if parsing fails.
"""
function parse_column_name(
    column_name::String, 
    format::String, 
    mappings::SensorMappings
)::Union{SensorColumn, Nothing}
```

### Error Handling
- Use try-catch blocks for file operations and parsing
- Provide informative error messages
- Use @warn for non-critical issues
- Handle missing or invalid data gracefully

### Code Organization
- Modular design with clear separation of concerns
- Configuration handling in `CleanMastConfig`
- Data processing in `MastTimeSeries`
- CLI in main `CleanMast.jl`

### Testing
- Unit tests for core functionality
- Test both valid and invalid cases
- Test default values and edge cases
- Organized test sets for different components

## Dependencies

- YAML: For configuration file parsing
- DataFrames: For data manipulation
- CSV: For reading CSV files
- ArgParse: For command line argument parsing

## Contributing

When contributing to this project:
1. Follow the established code standards
2. Add tests for new functionality
3. Update documentation as needed
4. Use clear commit messages
5. Create feature branches for new development

## Future Development

Priority areas for development:
1. Implementation of data cleaning rules
2. Enhanced validation and error reporting
3. Time series analysis features
4. Performance optimization for large datasets
5. Additional output formats

## Project Goals

The ultimate goal is to provide a robust, flexible, and user-friendly tool for:
- Parsing various wind mast data formats
- Cleaning and validating data
- Generating standardized outputs
- Supporting data analysis workflows

```

Would you like me to:
1. Add more details to any section?
2. Add example usage scenarios?
3. Add more technical specifications?
4. Include troubleshooting guidelines?
