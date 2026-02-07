# Subagents Specification

LLM-powered agents for the Preprocess Mast Agent system.

---

## Table of Contents

- [Header & Sensor Format Recognizer](#header--sensor-format-recognizer)
- [Location Extractor](#location-extractor)
- [Warning Collector](#warning-collector)
- [Summary Generator](#summary-generator)

---

## Header & Sensor Format Recognizer

Analyzes file header region to extract column names and sensor metadata.

### Domain Knowledge

**Understanding Header Structure Variations:**

Wind measurement data files have highly variable header structures. Unlike standardized formats like JSON or XML, CSV headers from different equipment manufacturers vary significantly:

1. **Simple Headers**: Single line with column names
   - Example: `Timestamp,WS_80m,WD_80m,Temp_10m`

2. **Multi-line Headers**: Equipment metadata + column names
   - Lines 1-3: Site info, equipment serial numbers, calibration dates
   - Line 4: Column names
   - Line 5: Units (optional)

3. **Lidar Headers**: Complex attribute blocks
   - Multiple sections with key-value pairs
   - Column names embedded in attribute blocks
   - Different structure per manufacturer (WindCube, ZephIR, etc.)

4. **Localized Headers**: Non-English column names
   - Chinese: `时间,风速80米,风向80米,温度`
   - German: `Zeitstempel,Windgeschwindigkeit,Windrichtung`
   - Mixed: `Timestamp,风速,WD_80m`

**Column Metadata Extraction:**

The LLM is provided with the `SensorColumn` type definition from the codebase and asked to extract columns that match this schema:
- `sensor_type`: WindSpeed, WindDirection, Temperature, Pressure, RelativeHumidity, DataAvailability, Timestamp
- `height`: Measurement height in meters
- `stat_type`: avg, min, max, std, count
- `unit`: m/s, deg, C, hPa, %, etc.
- `sensor_direction`: N/A or cardinal direction

**Note on Availability**: In the codebase, availability is a `sensor_type` "DataAvailability" (not "Availability"), not a `stat_type`. The `stat_type` for availability columns is typically "avg" (representing average availability percentage).

**Essential Columns Rule**: Any column with valid, complete metadata (all fields populated correctly) is considered **essential** for grouping. This includes:
- Timestamp columns
- Wind speed/direction columns  
- Temperature, pressure, relative humidity (if present)
- DataAvailability columns (for Lidar - required for data cleaning)

Files can be in the same group if they share all essential columns. Columns with incomplete or ambiguous metadata are not essential.

**Column Name Recognition:**

The LLM recognizes columns from the header and extracts their metadata. Column names in the source files may vary (e.g., `WS_80m`, `WS80`, `WindSpeed_80m`), but during **grouping phase**, we use **exact substring matching** - files must have the same column names to be grouped together.

Column name normalization/renaming happens later during **Phase 5 (Intra-Group Merging)**. See [plan.md](plan.md) for workflow details.

**Header Line Ambiguity:**

In multi-line headers, it's not always obvious which line contains column names:
- Line with units (m/s, degrees) is NOT the column name line
- Line with mostly short words might be column names
- Line matching data column count is likely the header

### Types

#### Input

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | `Path` | Path to CSV/dat file |
| `data_beginning_linenum` | `int` | From Data Range Detector (0-indexed) |
| `lines_above` | `int` | Default: 5, lines to read above data start |
| `lines_below` | `int` | Default: 2, data lines to include for context |
| `delimiter` | `Optional[str]` | Optional delimiter hint (comma, tab, semicolon, pipe) |

#### Output

| Field | Type | Description |
|-------|------|-------------|
| `header_linenum` | `int` | Line number containing column names (0-indexed) |
| `timestamp_mode` | `enum` | `single` (one column) or `split` (date + time columns) |
| `timestamp_column` | `Optional[str]` | Name of timestamp column (when mode=single) |
| `date_column` | `Optional[str]` | Name of date column (when mode=split) |
| `time_column` | `Optional[str]` | Name of time column (when mode=split) |
| `timestamp_format` | `str` | Format string (e.g., "%Y-%m-%d %H:%M:%S" or "%Y-%m-%d" + "%H:%M:%S") |
| `delimiter` | `str` | Detected or confirmed delimiter |
| `columns` | `list[ColumnMetadata]` | All column definitions with variants |

#### ColumnMetadata

Matches the codebase `SensorColumn` type. All fields with good metadata are considered essential for grouping.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Original column name (no renaming) |
| `sensor_type` | `enum` | WindSpeed, WindDirection, Temperature, Pressure, RelativeHumidity, DataAvailability, Timestamp |
| `height` | `float` | Sensor height in meters (null for non-height sensors like Timestamp) |
| `stat_type` | `enum` | avg, min, max, std, count |
| `unit` | `str` | Measurement unit (m/s, deg, C, hPa, %, etc.) |
| `sensor_direction` | `str` | "N/A" or cardinal direction (N, NE, E, SE, S, SW, W, NW) |

**Note**: The LLM is provided with the SensorColumn type definition and asked to extract columns that match this schema. Any column with valid `sensor_type`, `height`, `stat_type`, and `unit` is considered to have "good metadata". During grouping, files must have exact matching column names (substring match). Column renaming/normalization happens later during Phase 5 (Intra-Group Merging). See [plan.md](plan.md) for workflow details.

### Steps

1. **Read Context Lines**
   - Read `lines_above` lines before `data_beginning_linenum`
   - Read `lines_below` data lines starting at `data_beginning_linenum`
   - Preserve line numbers for reference

2. **LLM Analysis**
   - Send lines to LLM with sensor type aliases context
   - Prompt includes common patterns (WS, WD, Anem, Vane, etc.)
   - Request structured output with column metadata
   - **Critical**: Identify timestamp/date/time columns and sensor columns that match SensorColumn type

3. **Timestamp Verification (Deterministic)**
   - Read a few data lines below `data_beginning_linenum`
   - Extract values from timestamp column(s)
   - **For single column**: Verify format matches pattern
   - **For split columns**: Verify date column + time column combine to valid datetime
   - If verification fails, try alternative timestamp interpretations

4. **Validation**
   - Verify timestamp column(s) exist and are parseable
   - Check at least one WindSpeed column found
   - Validate height values are positive numbers
   - Ensure at least one sensor column (with complete SensorColumn metadata) is identified

5. **Output Generation**
   - Produce structured result with column definitions
   - Mark essential vs non-essential columns
   - Include variant names for flexible matching

### Matching Strategy (For Format Matcher Tool)

The Header Recognizer output enables this matching logic:

```
To match a candidate file to reference:
1. Must have same delimiter
2. Must contain all essential columns (by name or variant)
3. Must have compatible timestamp format
4. Non-essential columns can differ
```

**Implementation approach:**

For each candidate file (deterministic, no LLM):
1. Read up to 10 lines above `data_beginning_linenum`
2. Split each line by delimiter
3. Collect all potential column names into a set
4. Check if all sensor columns from reference exist in the candidate
   - Exact substring matching (case-insensitive)
   - Must have same timestamp/date/time columns
   - Must have same sensor columns (WindSpeed, WindDirection, etc.)
   - Column renaming happens later in Phase 5 (see [plan.md](plan.md))
 5. Verify timestamp format in sample data lines

**Why this works:**
- We only run LLM on reference file (1 LLM call per iteration)
- LLM uses SensorColumn type as reference for what constitutes "good metadata"
- Other files are matched using exact substring matching (fast, deterministic)
- Reading 10 lines covers most header variations
- All files in group have identical column names, making Phase 5 merging straightforward
- Column renaming/normalization happens in Phase 5 (Intra-Group Merging), not during grouping

### Test Design

#### Unit Tests

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| Standard NRG header | 5 header lines + 2 data lines | Correct column count, types, heights; essential columns identified |
| Header with unit row | Header + unit row + data | `header_linenum` points to column names, not units |
| No height in column name | Columns without height suffix | LLM infers height from context or marks unknown |
| Multiple timestamp formats | Various date formats | Correctly identifies format string |
| Chinese column names | `时间,风速80米,风向80米` | Recognizes as timestamp, wind speed, wind direction; provides variants |
| Mixed essential/non-essential | `Timestamp,WS_80m,Equipment_ID,Temp_10m` | Marks Timestamp and WS_80m as essential; Equipment_ID as non-essential |
| **Split date/time columns** | `Date,Time,WS_80m,WD_80m` | `timestamp_mode=split`, `date_column=Date`, `time_column=Time` |
| **Single timestamp column** | `Timestamp,WS_80m,WD_80m` | `timestamp_mode=single`, `timestamp_column=Timestamp` |
| **Localized date/time** | `年月日,时分秒,风速,风向` | Recognizes Chinese date/time split format |

#### Integration Tests

| Scenario | Description |
|----------|-------------|
| Lidar vs mast headers | Different header patterns for equipment types |
| Chinese vs English headers | Localization handling |
| Malformed headers | Missing columns, extra commas |
| Equipment replacement | Same mast, different sensor configs; should identify common essential columns |
| Multi-manufacturer sites | Files from different loggers at same site |

#### Critical Test Cases for Matching

| Scenario | Reference File | Candidate File | Should Match? |
|----------|---------------|----------------|---------------|
| Same format, different order | `Timestamp,WS_80m,WD_80m` | `WD_80m,Timestamp,WS_80m` | Yes |
| Same essential, extra columns | `Timestamp,WS_80m` | `Timestamp,WS_80m,Temp_10m` | Yes |
| Variant names | `Timestamp,WS_80m` | `Time,WindSpeed_80m` | Yes (if variants provided) |
| Different delimiter | `Timestamp,WS_80m` (comma) | `Timestamp;WS_80m` (semicolon) | No |
| Missing essential | `Timestamp,WS_80m` | `Timestamp,Temp_10m` | No |
| Different timestamp format | `2024-01-01 12:00:00` | `01/01/2024 12:00` | No |

### Edge Cases

| Case | Handling |
|------|----------|
| **No header found** | Return error, suggest manual configuration |
| **Ambiguous sensor types** | Mark confidence low, include multiple possibilities |
| **Mixed height units** | Normalize to meters, note original unit |
| **Duplicate column names** | Append suffix (_1, _2), log warning |
| **Empty columns** | Skip with warning |
| **Binary/encoded headers** | Detect encoding issues, suggest Encoding Converter |
| **No columns with good metadata** | Reject - must have at least timestamp + one sensor with complete SensorColumn metadata |

### Implementation Notes

**LLM Prompt Considerations:**
- Must include comprehensive alias lists for sensor types
- Should request explicit essential/non-essential classification
- Must handle multi-language inputs
- Should provide confidence scores for ambiguous classifications

**Performance Considerations:**
- One LLM call per reference file
- Matching is O(n) text search (fast)
- Variant lists should be cached per reference

**Validation Requirements:**
- Essential columns must include timestamp
- At least one WindSpeed or WindDirection should be essential
- Variant lists should not be empty
- All variant names should be lowercase for case-insensitive matching

---

## Location Extractor

Extracts geographic location from file headers, metadata, or associated files.

### Domain Knowledge

**Coordinate Systems in Wind Energy:**

Wind farms operate globally, encountering various coordinate representations:

1. **WGS84 (Global Standard)**
   - Decimal: `39.9042, 116.4074` (most common)
   - DMS: `39°54'15.12"N, 116°24'26.64"E` (legacy reports)
   - Common in: International projects, GPS devices

2. **CGCS2000 (China)**
   - 3-degree Gauss-Kruger zones
   - Format: Zone + X + Y (e.g., `Zone 39, X=39512345.67, Y=3367890.12`)
   - Common in: Chinese wind farms
   - Requires conversion to WGS84

3. **Local Grid Systems**
   - Project-specific coordinate systems
   - Format: `EX=1000.0, EY=2000.0` (local easting/northing)
   - Common in: Engineering surveys, construction plans
   - Requires transformation parameters

4. **Geohash (Compact)**
   - Base32 encoding: `wx4g0b9c`
   - Precision varies by length (8 chars ≈ 20m accuracy)
   - Sometimes embedded in filenames

**Location Metadata Locations:**

Coordinates can appear in various places:
- Header lines (most common)
- Footer lines (less common)
- Separate metadata files (.txt, .xml, .json)
- Filename (e.g., `mast_wx4g0b9_siteA.csv`)
- Embedded in comments or notes

**Precision and Accuracy:**
- Wind farm scale: ±10m accuracy is sufficient
- Individual mast location: ±1m preferred
- Coordinates from different sources may differ by 10-100m
- Datum shifts can cause systematic offsets

### Types

#### Input

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | `Path` | Path to CSV/dat file |
| `data_beginning_linenum` | `int` | From Data Range Detector |
| `data_end_linenum` | `Optional[int]` | From Data Range Detector |
| `soft_char_limit` | `int` | Default: 6000, threshold for chunk size |
| `associated_files` | `list[Path]` | Metadata files in same directory |

#### Output

| Field | Type | Description |
|-------|------|-------------|
| `location` | `Optional[Location]` | Extracted location or null |
| `source` | `LocationSource` | Where location was found |
| `confidence` | `enum` | high, medium, low |
| `warnings` | `list[str]` | Any issues during extraction |

#### Location

| Field | Type | Description |
|-------|------|-------------|
| `latitude` | `float` | WGS84 latitude (-90 to 90) |
| `longitude` | `float` | WGS84 longitude (-180 to 180) |
| `geohash` | `Optional[str]` | Geohash string (precision 8+) |
| `crs` | `str` | Coordinate reference system (always "WGS84") |

#### LocationSource

| Field | Type | Description |
|-------|------|-------------|
| `type` | `enum` | header, footer, metadata_file, filename, geohash_file |
| `line_numbers` | `list[int]` | Lines where location was found |
| `file_path` | `Optional[Path]` | Source file if not main file |

#### CoordinateFormat (LLM Output)

| Field | Type | Description |
|-------|------|-------------|
| `format_type` | `enum` | lat_lon, cgcs2000_3degree, ex_ey, geohash, none |
| `value_1` | `Optional[str]` | First value (lat, X, EX, geohash) |
| `value_2` | `Optional[str]` | Second value (lon, Y, EY) or null |
| `zone` | `Optional[int]` | Zone number for CGCS2000 |
| `raw_lines` | `list[int]` | Source line numbers |

### Steps

1. **Chunk Reading - Above Data**
   - Start from `data_beginning_linenum - 1`
   - Read whole lines backward until `soft_char_limit` exceeded
   - Create chunk with line content array and line numbers
   - Continue if more content, creating multiple chunks

2. **Chunk Reading - Below Data** (if `data_end_linenum` provided)
   - Start from `data_end_linenum + 1`
   - Read whole lines forward until `soft_char_limit` exceeded
   - Create chunks with line content and numbers

3. **LLM Extraction per Chunk**
   - Send each chunk to LLM with coordinate format hints
   - LLM returns `CoordinateFormat` or `none`
   - Track which lines contained coordinates

4. **Coordinate Conversion**
   - **lat_lon**: Parse as WGS84 directly
   - **cgcs2000_3degree**: Use pyproj to convert zone+X+Y to WGS84
   - **ex_ey**: Convert local grid to WGS84 using pyproj
   - **geohash**: Decode to lat/lon using geohash library

5. **Result Aggregation**
   - First valid location wins
   - If multiple locations found, use first with warning
   - If no location found, return null

6. **Warning Generation**
   - Multiple locations detected
   - Low confidence extraction
   - Conversion warnings (datum shifts, etc.)

### Usage Note

Location extraction is performed during **Phase 4 (Format Grouping)** on the reference file only, and stored in `group_info.toml` for informational purposes. However, **location is NOT used for grouping** - files are grouped purely by header format (column names, count, delimiter).

Location data becomes relevant in **Phase 6 (Inter-Group Merging)** where groups may be merged or kept separate based on location compatibility. See [plan.md](plan.md) for workflow details.

### Test Design

#### Unit Tests

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| Lat/lon in header | Header with "Lat: 39.9, Lon: 116.4" | WGS84 coordinates, high confidence |
| CGCS2000 3-degree | Zone 39, X/Y coordinates | Converted WGS84, medium confidence |
| Geohash in filename | "mast_wx4g0b9.csv" | Decoded coordinates, source=filename |
| EX/EY format | Local grid coordinates | Converted WGS84 with note |
| No coordinates | Clean header | null location, no warnings |
| Multiple locations | Header and footer differ | First location + warning |
| **Split date/time columns** | `Date,Time,WS_80m,WD_80m` | `timestamp_mode=split`, `date_column=Date`, `time_column=Time` |

#### Integration Tests

| Scenario | Description |
|----------|-------------|
| Chinese wind farm files | CGCS2000 coordinates common |
| European sites | WGS84 or local datums |
| Lidar metadata | Separate .txt files with coordinates |
| Batch processing | Consistency across file groups |

### Edge Cases

| Case | Handling |
|------|----------|
| **No coordinates found** | Return null location, no error |
| **Invalid coordinate values** | Log warning, skip invalid |
| **Multiple locations** | Use first, log warning with locations file path |
| **Conversion failure** | Log warning, return raw format if possible |
| **Ambiguous format** | Mark low confidence, request manual review |
| **Coordinates in binary data** | Skip with warning |

---

## Warning Collector

Aggregates and categorizes warnings throughout the workflow.

### Purpose

Centralized warning collection for:
- Tracking issues without failing the workflow
- Generating summary reports
- Enabling manual review of quarantined files

### Types

#### WarningEntry

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `str` | ISO 8601 timestamp |
| `level` | `enum` | INFO, WARNING, ERROR |
| `category` | `str` | Warning category (see below) |
| `phase` | `str` | Workflow phase where warning occurred |
| `file` | `Optional[str]` | Related file path |
| `message` | `str` | Human-readable description |
| `context` | `Optional[dict]` | Additional structured data |

#### WarningCategories

| Category | Description | Example |
|----------|-------------|---------|
| `BINARY_FILE` | Binary file detected | "Binary file detected, moved to quarantine" |
| `ENCODING_CONVERSION` | Non-UTF8 file converted | "Converted from GB2312 to UTF-8" |
| `DATA_RANGE_FAILED` | Could not detect data boundaries | "No timestamp pattern found" |
| `MAX_GROUPING_ITERATIONS` | Grouping did not converge | "10 iterations reached, 3 files ungrouped" |
| `HEADER_RECOGNITION_FAILED` | Could not parse header | "No recognizable column names" |
| `LOCATION_EXTRACTION_LOW_CONFIDENCE` | Location found but uncertain | "Coordinates may be in local grid" |
| `MULTIPLE_LOCATIONS` | Different locations in group | "Header and footer have different coordinates" |
| `DUPLICATE_COLUMN_NAMES` | Column names duplicated | "Column 'WS_80m' appears twice" |
| `MISSING_SENSOR_TYPE` | Could not determine sensor type | "Column 'Aux_1' has unknown type" |
| `MERGE_CONFLICT` | Issues during merge | "Overlapping timestamps with different values" |

### Interface

```python
class WarningCollector:
    def add(self, category: str, message: str, level: str = "WARNING", 
            file: str = None, context: dict = None) -> None
    
    def get_by_category(self, category: str) -> list[WarningEntry]
    
    def get_by_phase(self, phase: str) -> list[WarningEntry]
    
    def get_counts(self) -> dict[str, int]
    
    def to_jsonl(self, log_path: Path) -> None
    
    def generate_summary(self) -> WarningSummary
```

### Output Format

JSONL (one JSON object per line):

```json
{"timestamp": "2026-02-03T10:00:00Z", "level": "WARNING", "category": "BINARY_FILE", "phase": "encoding", "file": "mast-A/data.bin", "message": "Binary file detected, moved to quarantine"}
{"timestamp": "2026-02-03T10:00:01Z", "level": "ERROR", "category": "MAX_GROUPING_ITERATIONS", "phase": "grouping", "file": "mast-A/", "message": "10 iterations reached, 3 files require manual review", "context": {"ungrouped_count": 3, "total_files": 15}}
```

---

## Summary Generator

Generates final processing report for a mast.

### Purpose

- Summarize processing results
- List quarantined files with reasons
- Provide actionable next steps
- Enable manual review workflow

### Types

#### ProcessingSummary

| Field | Type | Description |
|-------|------|-------------|
| `mast_name` | `str` | Mast directory name |
| `start_time` | `str` | ISO 8601 start timestamp |
| `end_time` | `str` | ISO 8601 end timestamp |
| `duration_seconds` | `float` | Total processing time |
| `phases_completed` | `list[str]` | Successfully completed phases |
| `output_files` | `list[OutputFile]` | Generated output files |

#### ProcessingStats

| Field | Type | Description |
|-------|------|-------------|
| `total_input_files` | `int` | Files found in pre-masts/{mast}/ |
| `processed_files` | `int` | Files successfully processed |
| `quarantined_files` | `int` | Files moved to quarantine |
| `grouped_files` | `int` | Files assigned to groups |
| `manual_review_files` | `int` | Files in group-manual-review/ |
| `success_rate` | `float` | processed / total |

#### QuarantineSummary

| Field | Type | Description |
|-------|------|-------------|
| `total_quarantined` | `int` | Total files quarantined |
| `by_category` | `dict[str, int]` | Count per quarantine category |
| `files` | `list[QuarantinedFile]` | Details per file |

#### QuarantinedFile

| Field | Type | Description |
|-------|------|-------------|
| `original_path` | `str` | Original file location |
| `quarantine_path` | `str` | Current location in quarantine/ |
| `category` | `str` | Quarantine reason category |
| `reason` | `str` | Human-readable reason |
| `recoverable` | `bool` | Can be manually fixed and reprocessed |

#### GroupSummary

| Field | Type | Description |
|-------|------|-------------|
| `total_groups` | `int` | Number of format groups |
| `groups` | `list[GroupInfo]` | Per-group details |

#### GroupInfo

| Field | Type | Description |
|-------|------|-------------|
| `group_id` | `str` | Group identifier (e.g., "group-abc123") |
| `file_count` | `int` | Number of files in group |
| `files` | `list[str]` | File names |
| `location` | `Optional[Location]` | Extracted location |
| `sensor_count` | `int` | Number of sensors detected |
| `time_range` | `Optional[TimeRange]` | Min/max timestamps |

#### WarningSummary

| Field | Type | Description |
|-------|------|-------------|
| `total_warnings` | `int` | Total warning count |
| `total_errors` | `int` | Total error count |
| `by_category` | `dict[str, int]` | Count per category |
| `critical_issues` | `list[str]` | Issues requiring attention |

#### NextSteps

| Field | Type | Description |
|-------|------|-------------|
| `actions` | `list[str]` | Recommended actions |
| `manual_review_required` | `bool` | True if files need manual review |
| `review_files` | `list[str]` | Files requiring review |

### Report Format

```json
{
  "mast_name": "M01",
  "start_time": "2026-02-03T10:00:00Z",
  "end_time": "2026-02-03T10:15:30Z",
  "duration_seconds": 930.5,
  "phases_completed": ["discovery", "encoding", "data-range", "grouping", "merging", "output"],
  "stats": {
    "total_input_files": 20,
    "processed_files": 17,
    "quarantined_files": 3,
    "grouped_files": 17,
    "manual_review_files": 0,
    "success_rate": 0.85
  },
  "quarantine": {
    "total_quarantined": 3,
    "by_category": {
      "BINARY_FILE": 1,
      "DATA_RANGE_FAILED": 2
    },
    "files": [
      {
        "original_path": "pre-masts/M01/corrupted.dat",
        "quarantine_path": "pre-masts/M01/quarantine/binary/corrupted.dat",
        "category": "BINARY_FILE",
        "reason": "Binary file detected",
        "recoverable": false
      }
    ]
  },
  "groups": {
    "total_groups": 2,
    "groups": [
      {
        "group_id": "group-abc123",
        "file_count": 10,
        "files": ["jan.csv", "feb.csv", ...],
        "sensor_count": 8,
        "time_range": {"start": "2024-01-01", "end": "2024-06-30"}
      }
    ]
  },
  "warnings": {
    "total_warnings": 5,
    "total_errors": 0,
    "by_category": {
      "ENCODING_CONVERSION": 3,
      "LOCATION_EXTRACTION_LOW_CONFIDENCE": 2
    },
    "critical_issues": []
  },
  "output_files": [
    {"path": "masts/M01/data.parquet", "format": "parquet", "size_bytes": 1234567},
    {"path": "masts/M01/data.csv", "format": "csv", "size_bytes": 2345678},
    {"path": "masts/M01/sensors.toml", "format": "toml", "size_bytes": 1234}
  ],
  "next_steps": {
    "actions": ["Review quarantined files", "Validate output in CleanMast"],
    "manual_review_required": false,
    "review_files": []
  }
}
```

---

## Future Subagents

Potential additional subagents to consider:

| Subagent | Purpose | Priority |
|----------|---------|----------|
| **Data Quality Assessor** | Flag suspicious data patterns for human review | Medium |
| **Sensor Grouping Analyzer** | Determine which files belong to same mast/lidar | High |
| **Timestamp Pattern Detector** | Identify irregular timestamp formats | Medium |
| **Unit Normalizer** | Convert between different unit conventions | Low |
