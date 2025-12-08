# CSV Merger

Merges multiple CSV files from a directory into a single file with timestamp normalization and duplicate detection.

## Usage

```bash
uv run csv-merger path/to/config.toml
```

## Features

- **Automatic File Discovery**: Scans directory for all CSV files
- **Encoding Detection**: Auto-detects and converts file encodings to UTF-8
- **Flexible Header Detection**: Find headers by line number or regex pattern
- **Timestamp Normalization**: Converts various datetime formats to standardized `YYYY-MM-DD HH:MM:SS`
- **Duplicate Detection**: Warns about duplicate timestamps
- **Sorted Output**: Chronologically sorted merged data
- **Column Validation**: Ensures all files have consistent column structures

## Configuration File Format

```toml
# Output file path (relative to config file location)
output = "merged_output.csv"

[input]
# Directory containing CSV files to merge
dir = "path/to/csv/files"

# Field delimiter (optional, defaults to comma)
delim = ","  # Use "\t" for tab-delimited files

# Option 1: Combined datetime column
[input.datetime]
format = "%Y/%m/%d %H:%M"
col = "Date Time"

# OR Option 2: Separate date and time columns
# [input.date]
# format = "%Y/%m/%d"
# col = "Date"
#
# [input.time]
# format = "%H:%M"
# col = "Time"

# Header detection (choose ONE method)

# Method 1: Specific line number (0-based indexing)
[input.headline]
number = 3  # Use the 4th line as header

# OR Method 2: Regex pattern to find header line
# [input.headline]
# regex = "^Date Time,Battery"
```

## Parameters

### Root Level

- **output**: Path to output merged CSV file (relative to config file)

### [input] Section

- **dir**: Directory containing CSV files to merge
- **delim**: Field delimiter (default: `","`, use `"\t"` for tab-separated files)
- **patterns**: List of file patterns to match (default: `["*.csv"]`, e.g., `["*.wnd"]`, `["*.csv", "*.dat"]`)
- **datetime**: Single datetime column configuration (mutually exclusive with date/time)
- **date**: Date column configuration (requires time as well)
- **time**: Time column configuration (requires date as well)
- **headline**: Header detection configuration

### [input.datetime] Section

Used when datetime is in a single column.

- **col**: Name of the datetime column
- **format**: Python datetime format string (e.g., `"%Y/%m/%d %H:%M"`)

### [input.date] and [input.time] Sections

Used when date and time are in separate columns.

- **col**: Name of the date/time column
- **format**: Python datetime format string

### [input.headline] Section

Specify exactly one method:

- **number**: Line number containing headers (0-based indexing)
- **regex**: Regex pattern to match header line

## Example: Tab-Delimited Wind Data Files

For Kintech .wnd files with tab delimiters and header on line 4:

```toml
output = "merged_wind_data.csv"

[input]
dir = "."
delim = "\t"
patterns = ["*.wnd"]

[input.datetime]
col = "Date Time"
format = "%Y/%m/%d %H:%M"

[input.headline]
number = 3  # 4th line (0-based)
```

## Example: Comma-Delimited with Separate Date/Time

```toml
output = "merged_mast_data.csv"

[input]
dir = "raw_data"
delim = ","

[input.date]
col = "Date"
format = "%Y/%m/%d"

[input.time]
col = "Time"
format = "%H:%M"

[input.headline]
regex = "^Date,Time,Battery"
```

## Output Format

The merged CSV file will have:

- **Timestamp** column in standardized format (`YYYY-MM-DD HH:MM:SS`)
- All other columns from the input files
- Rows sorted chronologically by timestamp
- UTF-8 encoding

## Datetime Format Strings

Common Python datetime format codes:

- `%Y`: 4-digit year (2024)
- `%m`: 2-digit month (01-12)
- `%d`: 2-digit day (01-31)
- `%H`: 2-digit hour, 24-hour format (00-23)
- `%M`: 2-digit minute (00-59)
- `%S`: 2-digit second (00-59)

Examples:
- `"%Y/%m/%d %H:%M"` → `2024/02/28 13:45`
- `"%Y-%m-%d %H:%M:%S"` → `2024-02-28 13:45:30`
- `"%m/%d/%Y %I:%M %p"` → `02/28/2024 01:45 PM`

## Error Handling

The tool provides detailed error messages for:

- Missing or invalid configuration files
- Directory not found or no CSV files
- Column structure mismatches between files
- Header line not found (when using regex)
- Invalid datetime formats

Warnings are displayed for:

- Duplicate timestamps (with details)
- Encoding conversions

## Workflow Example

```bash
# 1. Create configuration file
cat > merge_config.toml <<EOF
output = "merged.csv"

[input]
dir = "mast_data_files"
delim = "\t"

[input.datetime]
col = "Date Time"
format = "%Y/%m/%d %H:%M"

[input.headline]
number = 3
EOF

# 2. Run merger
uv run csv-merger merge_config.toml

# Output: merged.csv with all data chronologically sorted
```
