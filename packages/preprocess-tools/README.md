# Preprocess Tools

Generic CSV preprocessing utilities for wind measurement data.

This package provides command-line tools to normalize and merge mast data files:

1. **CSV Merger**: Merges multiple CSV files with timestamp normalization
2. **Type Normalizer**: Converts string columns to float types
3. **Column Name Normalizer**: Renames columns to standardized formats (NRG, Lidar)
4. **Timestamp Normalizer**: Normalizes timestamp formats

## Installation

From the workspace root:

```bash
uv sync
```

## Usage

The package provides a unified CLI with subcommands:

```bash
# Show all available commands
uv run preprocess --help

# CSV Merging
uv run preprocess csv-merge path/to/merge-config.toml

# Column Name Normalization
uv run preprocess col-normalizer path/to/col-name-config.toml

# Type Normalization
uv run preprocess type-normalizer path/to/type-config.toml

# Timestamp Normalization
uv run preprocess timestamp path/to/timestamp-config.toml
```

## Documentation

- **[CSV Merger Reference](docs/csv-merger.md)** - Merge multiple CSV files
- **[Command Reference](docs/commands.md)** - Detailed command-line documentation
- **[NRG Format Guide](docs/nrg-format.md)** - NRG column header format
- **[Lidar Format Guide](docs/lidar-format.md)** - Lidar data format
- **[Contributing Guide](docs/contributing.md)** - Development guidelines

## Features

- **Type Safety**: Uses Pydantic for configuration validation
- **Flexible Path Handling**: Supports relative paths from config file location
- **Error Handling**: Graceful handling of missing columns and conversion errors
- **Progress Reporting**: Detailed output showing what was converted
- **Multiple File Formats**: Supports .csv and .dat files

## Migration Note

This package is part of the CleanMast workspace migration from Julia to Python.
It replaces the preprocessing functionality previously in `py-preprocess-tools`.

For the full CleanMast pipeline, see the main workspace README.
