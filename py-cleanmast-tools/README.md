# Pre-processor for Mast Data

This project provides two command-line tools to normalize mast data files:

1. **Type Normalizer**: Converts string columns to float types
2. **Column Name Normalizer**: Renames columns to NRG format

## Installation

Install the project in development mode:

```bash
uv pip install -e .
```

## Usage

### Step 1: Type Normalization

Convert string columns (like wind speed and direction) to float types:

```bash
uv run type-normalizer path/to/type-config.toml
```

### Step 2: Column Name Normalization

Convert column names to standardized NRG format:

```bash
uv run col-name-normalizer path/to/col-name-config.toml
```

## Example Workflow

For the sample data files in `datas/by/`:

```bash
# Process 2501 data
uv run type-normalizer datas/by/type-config-2501.toml
uv run col-name-normalizer datas/by/col-name-config-2501.toml

# Process 2502 data
uv run type-normalizer datas/by/type-config-2502.toml
uv run col-name-normalizer datas/by/col-name-config-2502.toml
```

## Documentation

- **[Command Reference](docs/commands.md)** - Detailed command-line tool documentation
- **[NRG Format Guide](docs/nrg-format.md)** - NRG column header format specification
- **[Contributing Guide](docs/contributing.md)** - Development and contribution guidelines

## Quick Configuration Reference

Configuration files are placed in the same directory as the data files. Paths in the config files are relative to the config file location.

See [Command Reference](docs/commands.md) for complete configuration documentation.

## Output

The tools produce normalized CSV files with:
- Proper float data types for numeric columns
- Standardized NRG column names following the pattern: `Ch{channel}_{sensorType}_{height}m_{statType}_{unit}`

## Features

- **Type Safety**: Uses Pydantic for configuration validation
- **Flexible Path Handling**: Supports relative paths from config file location
- **Error Handling**: Graceful handling of missing columns and conversion errors
- **Progress Reporting**: Detailed output showing what was converted
- **Multiple File Formats**: Supports .csv and .dat files

## Project Structure

```
pre-processor-mast-data/
├── pre_processor_mast_data/    # Main package
│   ├── __init__.py
│   ├── type_normalizer.py      # Type normalization tool
│   └── col_name_normalizer.py  # Column name normalization tool
├── datas/by/                   # Sample data and configurations
│   ├── *.dat                   # Original data files
│   ├── *_type_normalized.csv   # Type-normalized outputs
│   ├── *_nrg_format.csv       # Final NRG-formatted outputs
│   └── *.toml                 # Configuration files
├── docs/                       # Documentation
│   ├── commands.md             # Command reference
│   ├── nrg-format.md          # NRG format specification
│   └── contributing.md        # Development guidelines
├── pyproject.toml             # Project configuration
└── README.md                  # This file
```