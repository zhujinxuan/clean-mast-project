# Tools Specification

Deterministic CLI tools for the Preprocess Mast Agent system.

---

## Table of Contents

- [Encoding Converter](#encoding-converter)
- [Data Range Detector](#data-range-detector)
- [Format Matcher](#format-matcher)
- [CSV Merger](#csv-merger)
- [Column Name Normalizer](#column-name-normalizer)
- [Type Normalizer](#type-normalizer)
- [Timestamp Normalizer](#timestamp-normalizer)
- [Format Converter](#format-converter)
- [Sensors TOML Writer](#sensors-toml-writer)
- [Smart Group Merger](#smart-group-merger)

---

## Encoding Converter

Converts file encoding to UTF-8 using chardet for detection.

### Purpose

Ensure all input files are in UTF-8 encoding before further processing.

### CLI Interface

```bash
encoding-converter pre-masts/{mast-name} --quarantine-dir pre-masts/{mast-name}/quarantine/
```

### Behavior

1. **Scan Directory**: Recursively scan `{mast-name}/` for all files (excluding hidden files and quarantine/)
2. **Detect Encoding**: Use chardet for each file
3. **Classify and Handle**:
   - **UTF-8/ASCII** (confidence ≥ 0.9): Keep in place, no action
   - **Non-UTF8 text** (confidence ≥ 0.7): Convert to UTF-8 in-place, move original to `quarantine/encoding/{charset}/`
   - **Low confidence** (0.5 ≤ confidence < 0.7): Convert with warning, move original to `quarantine/encoding/{charset}/`
   - **Very low confidence** (< 0.5) or **binary detected**: Move to `quarantine/binary/`, no conversion
4. **Binary Detection**: Use heuristic (null bytes present OR non-printable ratio > 30%)

### Output

Returns JSON report to stdout:

```json
{
  "mast_name": "M01",
  "phase": "encoding",
  "processed_files": [
    {
      "file": "data1.csv",
      "action": "converted",
      "source_encoding": "GB2312",
      "confidence": 0.95,
      "quarantine_path": "quarantine/encoding/gb2312/data1.csv"
    },
    {
      "file": "data2.csv",
      "action": "unchanged",
      "source_encoding": "UTF-8",
      "confidence": 1.0
    },
    {
      "file": "corrupted.dat",
      "action": "quarantined",
      "reason": "BINARY_FILE",
      "quarantine_path": "quarantine/binary/corrupted.dat"
    }
  ],
  "summary": {
    "total": 10,
    "converted": 3,
    "unchanged": 6,
    "quarantined": 1
  }
}
```

### Directory Structure

```
pre-masts/{mast-name}/
├── [converted UTF-8 files]
└── quarantine/
    ├── encoding/
    │   ├── gb2312/
    │   │   └── original_file.csv
    │   ├── latin1/
    │   └── windows-1252/
    └── binary/
        └── corrupted.dat
```

### Error Handling

- **Single file failure**: Log error, continue processing other files
- **Critical failure** (e.g., directory not readable): Exit with error code
- **Idempotency**: On re-run, skip files already in UTF-8 (fast path)

---

## Data Range Detector

CLI tool to detect where data begins and ends in CSV-like files.

### Detection Logic

**Data begins:**
- First continuous 10 lines starting with 4 digits (normal timestamp like `2024-...`)
- OR first continuous 50 lines starting with 1 digit (weird formats like `m-d-yy` or numeric first column)

**Data ends:**
- Detect trailing non-data lines

**Delimiter guess:**
- Check frequency of comma, tab, semicolon, pipe

### Input (TOML/YAML/JSON)

```toml
files = [
  "C:/path/to/file1.csv",
  "C:/path/to/file2.csv"
]
```

### Output (TOML/YAML/JSON)

```toml
[[results]]
file = "C:/path/to/file1.csv"
success = true
data_beginning_linenum = 3      # 0-indexed (polars convention)
count_of_lines_after_data_ends = 0  # 0 = last line is data
delimiter = ","

[[results]]
file = "C:/path/to/file2.csv"
success = false
error = "Could not detect data range"
error_category = "NO_TIMESTAMP_PATTERN"
```

### Error Categories

| Category | Description | Action |
|----------|-------------|--------|
| `NO_TIMESTAMP_PATTERN` | No recognizable timestamp column | Quarantine |
| `EMPTY_FILE` | File has no content | Quarantine |
| `BINARY_CONTENT` | Non-text content detected | Quarantine |
| `TOO_FEW_LINES` | File has < 10 lines | Quarantine |

### CLI Usage

```bash
data-range-detect input.toml --output result.json --quarantine-dir quarantine/data-range-failed/
```

---

## Format Matcher

Groups files by format signature using LLM-powered header recognition + deterministic matching.

### Purpose

Iterative format detection workflow:
1. Pick random file from ungrouped set
2. LLM extracts format signature (header + location)
3. Match remaining files by signature
4. Repeat until all grouped or max iterations reached

### Types

#### Input

| Field | Type | Description |
|-------|------|-------------|
| `scan_directory` | `Path` | Directory to scan for files |
| `groups_directory` | `Path` | Where to create group subdirectories |
| `max_iterations` | `int` | Maximum grouping attempts (default: 10) |
| `file_patterns` | `list[str]` | Glob patterns (default: ["*.csv", "*.dat"]) |

#### Output

| Field | Type | Description |
|-------|------|-------------|
| `groups` | `list[Group]` | Successfully created groups |
| `manual_review` | `list[str]` | Files requiring manual review |
| `iterations_used` | `int` | Number of iterations performed |
| `converged` | `bool` | True if all files grouped |

#### Group

| Field | Type | Description |
|-------|------|-------------|
| `group_id` | `str` | Unique identifier (e.g., "group-abc123") |
| `directory` | `Path` | Path to group directory |
| `files` | `list[str]` | Files in this group |
| `format_signature` | `FormatSignature` | Detected format |
| `location` | `Optional[Location]` | Extracted location |

#### FormatSignature

| Field | Type | Description |
|-------|------|-------------|
| `column_names` | `list[str]` | List of column names from reference file |
| `timestamp_mode` | `enum` | `single` or `split` |
| `timestamp_column` | `Optional[str]` | Name of timestamp column (single mode) |
| `date_column` | `Optional[str]` | Name of date column (split mode) |
| `time_column` | `Optional[str]` | Name of time column (split mode) |
| `timestamp_format` | `str` | Format string(s) |
| `delimiter` | `str` | Delimiter character |

### Steps

1. **Initialize**
   - Scan directory for all matching files
   - Load existing state (if resuming)

2. **Iterative Grouping Loop** (max_iterations)
   - If no ungrouped files remaining → break
   - Pick random file from ungrouped set
   - Call Header Recognizer subagent → get format signature
   - For each remaining ungrouped file:
     - **Must have same delimiter**
     - **Extract candidate header columns**:
       - Read up to 10 lines above `data_beginning_linenum`
       - Split each line by delimiter
       - Collect all potential column names into a set
     - **Check essential columns present**:
       - For each essential column from reference
       - Check if any variant exists in candidate's column set
       - All essentials must be present
     - **Verify timestamp format** (deterministic, no LLM):
       - Read a few data lines below `data_beginning_linenum`
       - For `timestamp_mode=single`: Extract timestamp column values, verify format
       - For `timestamp_mode=split`: Extract date and time column values, verify combined format
       - Use Python datetime parsing or regex pattern matching
   - Move matched files to new group directory

3. **Handle Max Iterations**
   - If ungrouped files remain after max_iterations
   - Create `group-manual-review/` directory
   - Move remaining files there
   - Log MAX_GROUPING_ITERATIONS warning

4. **Output Generation**
   - Create group_info.toml in each group directory
   - Return grouping results

### Group Directory Structure

```
pre-masts/{mast-name}/
└── groups/
    ├── group-abc123/
    │   ├── file1.csv
    │   ├── file2.csv
    │   └── group_info.toml
    ├── group-def456/
    │   ├── file3.csv
    │   └── group_info.toml
    └── group-manual-review/
        ├── weird_file.csv
        └── README.txt
```

### group_info.toml

```toml
group_id = "group-abc123"
created_at = "2026-02-03T10:00:00Z"
file_count = 2
files = ["file1.csv", "file2.csv"]

[format_signature]
column_names = ["Timestamp", "WS_80m_Avg", "WD_80m_Avg", "Temp_10m_Avg"]
timestamp_mode = "single"
timestamp_column = "Timestamp"
timestamp_format = "%Y-%m-%d %H:%M:%S"
delimiter = ","

# Location is extracted but NOT used for grouping
# Groups may contain files from same or different locations
[location_from_reference]
latitude = 39.9042
longitude = 116.4074
confidence = "high"
source = "header"
```

### CLI Usage

```bash
format-matcher pre-masts/M01/ --groups-dir pre-masts/M01/groups/ --max-iterations 10
```

---

## CSV Merger

Merges multiple CSV files with timestamp normalization.

### Status

**Reference implementation** exists in `packages/preprocess-tools/`

### Note on Agentic Version

The existing implementation handles encoding detection, header detection, timestamp creation, and schema alignment. The agentic version will differ significantly:
- No encoding detection (handled in Phase 2)
- No header detection (handled by Header Recognizer subagent)
- Group-aware processing (files already grouped in `groups/group-*/`)
- State integration with workflow
- Schema validation only (grouping guarantees identical schemas)

Details of the agentic version will be specified separately.

### Reference

See: `packages/preprocess-tools/src/preprocess_tools/csv_merger.py`

---

## Column Name Normalizer

Renames columns to standardized formats (NRG, Lidar).

### Status

**Reference implementation** exists in `packages/preprocess-tools/`

### Note on Agentic Version

The existing implementation uses user-defined `column_mappings` from TOML config. The agentic version will differ:
- Mappings auto-generated from Header Recognizer's `ColumnMetadata` output
- Batch processing per-group (all files in group get same mapping)
- NRG-style naming convention (`Ch{N}_{SensorType}_{Height}m_{StatType}_{Unit}`)
- Preserves original names for sensors.toml generation

Details of the agentic version will be specified separately.

### Reference

See: `packages/preprocess-tools/src/preprocess_tools/col_name_normalizer.py`

---

## Type Normalizer

Converts string columns to numeric types.

### Status

**Reference implementation** exists in `packages/preprocess-tools/`

### Note on Agentic Version

The existing implementation uses user-defined `float_columns` from TOML config. The agentic version will differ:
- Auto-detects numeric columns from Header Recognizer's `ColumnMetadata`
- All sensor data (WindSpeed, WindDirection, Temperature, etc.) → Float64
- Timestamp columns handled separately
- Applied per-group after column normalization

Details of the agentic version will be specified separately.

### Reference

See: `packages/preprocess-tools/src/preprocess_tools/type_normalizer.py`

---

## Timestamp Normalizer

Normalizes timestamp formats.

### Status

**Reference implementation** exists in `packages/preprocess-tools/`

### Note on Agentic Version

The existing implementation uses user-defined `input_format` from TOML config. The agentic version will differ:
- Format auto-detected by Header Recognizer subagent
- Supports both `single` timestamp column and `split` date+time columns
- Standardizes to ISO format (`%Y-%m-%d %H:%M:%S`)
- Handles timezone conversion if needed

Details of the agentic version will be specified separately.

### Reference

See: `packages/preprocess-tools/src/preprocess_tools/timestamp_normalizer.py`

---

## Format Converter

Converts between different data formats (NRG, Lidar, generic CSV).

### Purpose

Transform data into standardized output format for CleanMast processing.

### Input

- Source data file(s) from merged groups
- Format specification (from Header Recognizer output)
- Target format (NRG, Lidar, or generic)

### Output

- Standardized `data.csv` with consistent column naming
- Separate `sensors.toml` with metadata

### Processing Steps

1. **Load Group Data**
   - Read merged data from each group
   - Load group_info.toml for metadata

2. **Schema Alignment**
   - Normalize column names across groups
   - Handle missing columns (fill with null)
   - Reorder columns consistently

3. **Smart Merge Groups**
   - Analyze timestamp overlap between groups
   - Determine merge strategy (see Smart Group Merger)

4. **Output Generation**
   - Write data.parquet (primary)
   - Write data.csv (compatibility)
   - Generate sensors.toml

### CLI Usage

```bash
format-converter pre-masts/M01/groups/ --output-dir masts/M01/ --format nrg
```

---

## Sensors TOML Writer

Writes sensor metadata to standardized TOML format.

### Purpose

Generate `sensors.toml` file from recognized column metadata.

### Input

- Header Recognizer output (ColumnMetadata list)
- Optional location data from Location Extractor
- User overrides (if any)

### Output

Complete `sensors.toml` file:

```toml
[location]
latitude = 39.9042
longitude = 116.4074
geohash = "wx4g0b9c"

[[sensors]]
name = "Ch1_Anem_80.00m_Avg_m/s"
sensor_type = "WindSpeed"
height = 80.0
stat_type = "avg"
unit = "m/s"
direction = "N/A"
original_name = "WS_80m_Avg"

[[sensors]]
name = "Ch2_Vane_80.00m_Avg_Deg"
sensor_type = "WindDirection"
height = 80.0
stat_type = "avg"
unit = "deg"
direction = "N/A"
original_name = "WD_80m_Avg"
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Normalized column name |
| `sensor_type` | Yes | WindSpeed, WindDirection, Temperature, Pressure, RelativeHumidity, DataAvailability |
| `height` | Yes | Sensor height in meters |
| `stat_type` | Yes | avg, min, max, std, count |
| `unit` | Yes | Unit string (m/s, deg, C, hPa) |
| `direction` | Yes | N/A or cardinal direction |
| `original_name` | No | Original column name from source file |

### CLI Usage

```bash
sensors-toml-writer --metadata group_info.toml --output sensors.toml
```

---

## Smart Group Merger

Analyzes and merges multiple format groups into final output.

### Purpose

Intelligently merge groups based on timestamp overlap and sensor complementarity.

### Merge Strategies

| Scenario | Strategy | Description |
|----------|----------|-------------|
| Same time, different sensors | Horizontal join | Join on timestamp, combine columns |
| Different time, same sensors | Vertical concat | Stack rows chronologically |
| Overlapping time, same sensors | Conflict resolution | Choose based on priority or average |
| Overlapping time, different sensors | Complex merge | Join + deduplicate |

### Input

| Field | Type | Description |
|-------|------|-------------|
| `groups` | `list[Group]` | Groups to merge |
| `merge_config` | `MergeConfig` | Configuration for merge behavior |

#### MergeConfig

| Field | Type | Description |
|-------|------|-------------|
| `on_conflict` | `enum` | Resolution strategy: priority, average, keep_first, keep_last |
| `priority_groups` | `list[str]` | Group IDs with priority (first = highest) |
| `tolerance_minutes` | `int` | Timestamp matching tolerance (default: 5) |

### Output

Single merged DataFrame with:
- All timestamps from all groups
- All unique sensors
- Conflicts resolved according to config

### Algorithm

1. **Analyze Groups**
   - Load each group's data
   - Extract time ranges
   - Identify sensor overlap

2. **Determine Merge Strategy per Group Pair**
   - Calculate timestamp overlap
   - Compare sensor sets
   - Select appropriate strategy

3. **Execute Merge**
   - Iteratively merge groups
   - Handle conflicts
   - Sort by timestamp

4. **Validation**
   - Check for duplicate timestamps
   - Verify all sensors present
   - Validate data ranges

### CLI Usage

```bash
smart-group-merger pre-masts/M01/groups/ --config merge_config.toml --output merged.parquet
```

---

## Tool Integration Strategy

### Option 1: Import from preprocess-tools

```python
from preprocess_tools.csv_merger import main as csv_merger
from preprocess_tools.col_name_normalizer import main as col_normalizer
# ... etc
```

**Pros:** No code duplication
**Cons:** Tight coupling, preprocess-tools may not expose clean API

### Option 2: Extract to shared package

Create `packages/preprocess-core/` with shared utilities.

**Pros:** Clean separation, reusable components
**Cons:** More packages to maintain

### Option 3: Reimplement for agent needs

Create agent-specific versions with different interfaces.

**Pros:** Optimized for agent workflow
**Cons:** Code duplication, maintenance burden

### Recommendation

**Start with Option 1**, refactor to Option 2 if preprocess-tools API is insufficient.

---

## New Tools Summary

| Tool | Status | Priority |
|------|--------|----------|
| Encoding Converter | ⏳ To be defined | High |
| Data Range Detector | ⏳ To be defined | High |
| Format Matcher | ⏳ To be defined | High |
| Smart Group Merger | ⏳ To be defined | Medium |
| Format Converter | ⏳ To be defined | Medium |
| Sensors TOML Writer | ⏳ To be defined | High |
