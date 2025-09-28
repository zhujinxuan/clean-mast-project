# Command Reference

This document provides detailed information about the command-line tools provided by the pre-processor-mast-data project.

## type-normalizer

Converts string columns to float types in mast data files.

### Usage

```bash
uv run type-normalizer path/to/type-config.toml
```

### Configuration File Format

The type normalizer uses a TOML configuration file with the following structure:

```toml
# Path to input data file (relative to config file location)
input_path = "input.dat"

# Path to output CSV file (relative to config file location)
output_path = "output_type_normalized.csv"

# Rows to skip: can be an integer (skip first N rows) or list of row indices
skip_rows = [1, 2]  # Skip rows 2 and 3 (0-based indexing)

# Header row number (0-based, after skipping rows)
header_row = 0

# Field delimiter (optional, defaults to comma)
delimiter = ","  # Use "\t" for TSV files

# List of column names to convert to float
float_columns = [
    "WS_130m_Avg", "WS_130m_Std", "WS_130m_Max", "WS_130m_Min",
    "WD_130m_Avg", "WD_130m_Std", "WD_130m_Max", "WD_130m_Min",
    "N", "E", "Al", "Batt_Volt",
    # ... more columns
]
```

### Parameters

- **input_path**: Path to the input CSV/DAT/TXT file
- **output_path**: Path to the output CSV file
- **skip_rows**: Rows to skip (int for first N rows, or list of 0-based indices)
- **header_row**: Row containing column headers (0-based, after skipping)
- **delimiter**: Field delimiter (optional, defaults to "," for CSV, use "\t" for TSV)
- **float_columns**: List of column names to convert to float type

### Example

```bash
# Process 2501 data
uv run type-normalizer datas/by/type-config-2501.toml
```

## col-name-normalizer

Converts column names to standardized NRG format.

### Usage

```bash
uv run col-name-normalizer path/to/col-name-config.toml
```

### Configuration File Format

The column name normalizer uses a TOML configuration file with the following structure:

```toml
# Path to input CSV file (relative to config file location)
input_path = "input_type_normalized.csv"

# Path to output CSV file (relative to config file location)
output_path = "output_nrg_format.csv"

# Rows to skip (usually 0 for already processed files)
skip_rows = 0

# Header row number (0-based)
header_row = 0

# Whether to keep columns not in the mapping
keep_unmapped = true

# Field delimiter (optional, defaults to comma)
delimiter = ","  # Use "\t" for TSV files

# Column name mappings from old names to new NRG format names
[column_mappings]
"TIMESTAMP" = "Timestamp"
"WS_130m_Avg" = "Ch1_Anem_130.00m_Avg_m/s"
"WS_130m_Std" = "Ch1_Anem_130.00m_SD_m/s"
"WD_130m_Avg" = "Ch13_Vane_130.00m_Avg_Deg"
# ... more mappings
```

### Parameters

- **input_path**: Path to the input CSV/TSV file
- **output_path**: Path to the output CSV file
- **skip_rows**: Rows to skip (int for first N rows, or list of 0-based indices)
- **header_row**: Row containing column headers (0-based, after skipping)
- **keep_unmapped**: Whether to keep columns not specified in mappings
- **delimiter**: Field delimiter (optional, defaults to "," for CSV, use "\t" for TSV)
- **column_mappings**: Dictionary mapping old column names to new NRG format names

### Example

```bash
# Process 2501 data
uv run col-name-normalizer datas/by/col-name-config-2501.toml
```

## Typical Workflow

1. **Type Normalization**: Convert string columns to float types
2. **Column Name Normalization**: Convert column names to NRG format

```bash
# Complete workflow for 2501 data
uv run type-normalizer datas/by/type-config-2501.toml
uv run col-name-normalizer datas/by/col-name-config-2501.toml
```

## Error Handling

Both tools provide detailed error messages and warnings:
- Missing columns are reported but don't stop processing
- Invalid data types are handled gracefully with `pd.to_numeric(errors='coerce')`
- Configuration validation errors are reported with specific details
- File path issues are clearly indicated
