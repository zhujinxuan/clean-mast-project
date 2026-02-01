# Preprocess Mast Agent

An LLM-powered agent for preprocessing wind measurement tower data directly to
parsed files (data CSV and sensors TOML).

## Project Structure

- Package location: `packages/preprocess-mast-agent/`
- New workspace member in the monorepo

## Coding Standards

- Same Python code standard as existing packages (pydantic, polars, click, etc.)
- Use `ty` instead of `pyright` for type checking
- Use Pydantic AI for LLM communication
- Use `.env` for OpenAI-compatible API configuration

## Domain Context

### Input Structure

User places raw data under `{project work dir}/pre-masts/`:

```
pre-masts/
├── mast-A/           # Each mast/lidar at different physical location
│   ├── raw1.csv
│   ├── raw2.csv
│   └── ...
├── mast-B/
│   └── ...
└── lidar-C/          # If equipment replaced at same location, same dir
    └── ...
```

### Output Structure

For each mast/lidar directory, produce:

1. **data.csv** - Merged, cleaned, normalized time series data
2. **sensors.toml** - Sensor metadata with column mappings

### sensors.toml Location Field

The output `sensors.toml` includes an optional location field:

```toml
[location]
latitude = 39.9042      # Optional
longitude = 116.4074    # Optional
geohash = "wx4g0b"      # Optional, ~meter accuracy (geohash precision 8+)
```

## Subagents and Tools

### Subagents (LLM-powered)

#### 1. Header & Sensor Format Recognizer

Analyze file header region to extract column names and sensor metadata.

**Input:**
- Single file path
- `data_beginning_linenum` from Data Range Detector

**Process:**
- Read 5 lines above `data_beginning_linenum` + 2 data lines
- Send these lines to LLM (not full content to avoid overwhelming)
- Prompt includes common sensor type aliases (WS, WD, T, P, etc.)

**Output:**
```toml
header_linenum = 2              # Where column names are (often data_line - 1)
                                # But may differ if unit/annotation lines exist

timestamp_column = "Date Time"
timestamp_format = "%Y-%m-%d %H:%M:%S"

[[columns]]
name = "Anem 80m Mean"          # Original column name (no renaming)
sensor_type = "WindSpeed"
height = 80.0
stat_type = "avg"
unit = "m/s"
sensor_direction = "N/A"

[[columns]]
name = "Vane 80m Mean"
sensor_type = "WindDirection"
height = 80.0
stat_type = "avg"
unit = "deg"
sensor_direction = "N/A"

[[columns]]
name = "Pressure"
sensor_type = "Pressure"
height = 2.0
stat_type = "avg"
# unit can be missing/null (e.g., for Pressure - normalization handled later)
sensor_direction = "N/A"

# ... more columns
```

**Notes:**
- Header line is normally `data_beginning_linenum - 1`, but sometimes there are
  unit rows or annotation rows between header and data
- A separate tool will handle grouping similar data files (to be discussed)

#### 2. Location Extractor

(To be discussed)

### Tools (Deterministic)

#### 1. Encoding Converter

Convert file encoding to UTF-8 using chardet for detection.

#### 2. Data Range Detector

CLI tool to detect where data begins and ends in CSV-like files.

**Detection Logic:**
- Data begins: First continuous 10 lines starting with 4 digits (normal timestamp
  like `2024-...`), OR first continuous 50 lines starting with 1 digit (weird
  formats like `m-d-yy` or numeric first column)
- Data ends: Detect trailing non-data lines
- Delimiter guess: Check frequency of comma, tab, semicolon, pipe

**Input (TOML/YAML/JSON):**
```toml
files = [
  "C:/path/to/file1.csv",
  "C:/path/to/file2.csv"
]
```

**Output (TOML/YAML/JSON):**
```toml
[[results]]
file = "C:/path/to/file1.csv"
data_beginning_linenum = 3      # 0-indexed (polars convention)
count_of_lines_after_data_ends = 0  # 0 = last line is data
delimiter = ","

[[results]]
file = "C:/path/to/file2.csv"
data_beginning_linenum = 5
count_of_lines_after_data_ends = 2  # 2 trailing lines to skip
delimiter = "\t"
```

**CLI Usage:**
```bash
data-range-detect input.toml --output result.json
# Output format auto-detected from extension (.toml/.yaml/.json)
```

#### 3. CSV Merger

(To be discussed)

#### 4. Column Name Normalizer

(To be discussed)

#### 5. Type Normalizer

(To be discussed)

#### 6. Timestamp Normalizer

(To be discussed)

#### 7. Format Converter

(To be discussed)

#### 8. Sensors TOML Writer

(To be discussed)

## Next Steps

(To be discussed in future sessions)

- Tool details and implementation
- Tool composition / pipeline design
- Pydantic AI agent configuration
- Error handling and retry logic
- User interaction points (confirmation, manual override)
- Testing strategy
