# CleanMast

Wind energy meteorological tower data analysis toolkit.

## Overview

CleanMast processes wind measurement data through a multi-stage pipeline:

- **Data Parsing**: Flexible sensor data parsing with configurable column mappings
- **Data Cleaning**: Range validation, layer difference checks, icing detection, tower shading
- **Data Reconstruction**: Single-mast correlation, mesoscale data integration, representative year calibration
- **Analysis & Reporting**: Wind resource assessment, EN standard compliance, quality reports

## Installation

From the workspace root:

```bash
# Install with all dependencies
uv sync --all-extras

# Or install specific extras
uv sync --extra analysis --extra visualization
```

## Usage

```bash
# Parse sensor data
uv run cleanmast parse-sensors --config parse-config.toml

# Process and clean data
uv run cleanmast process --config process-config.toml

# Generate reports
uv run cleanmast report --config report-config.toml
```

## Documentation

- **User Guide**: See `docs/user-guide/` (Chinese)
- **Development**: See `docs/development/`
- **Algorithms**: See `docs/algorithms/`

## Migration Status

This is the Python implementation of CleanMast, currently under active development.

For the stable Julia implementation, see `CleanMastProject/`.

### Current Status

- [ ] Parse Sensors - In planning
- [ ] Data Cleaning - Not started
- [ ] Reconstruction - Not started
- [ ] Analysis - Not started
- [ ] Reporting - Not started

See the workspace-level `docs/migration/` for detailed migration status.

## Architecture

```
cleanmast/
├── types/              # Core type definitions and configurations
├── parse_sensors/      # Data parsing and column mapping
├── process/            # Data cleaning rules and validation
├── reconstruct/        # Data reconstruction modules
├── analyze/            # Wind resource analysis
├── reports/            # Report generation
└── utils/              # Shared utilities
```

## Development

```bash
# Run tests
uv run pytest packages/cleanmast/tests

# Type checking
uv run pyright packages/cleanmast

# Linting
uv run ruff check packages/cleanmast
```

## Related Packages

- **preprocess-tools**: Generic CSV preprocessing utilities (encoding, merging, normalization)

This package depends on `preprocess-tools` for data preprocessing tasks.
