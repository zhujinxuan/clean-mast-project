# Preprocess Mast Data Skill

This skill automates the preprocessing of mast data using the py-cleanmast-tools pipeline.

## Overview

Preprocesses raw mast data files into clean, NRG-formatted CSV files ready for CleanMast analysis. The pipeline handles:

- CSV merging from multiple files
- Column name inconsistencies between files
- Type conversion (string to numeric)
- Metadata header removal
- Timestamp standardization
- **Duplicate timestamp detection and handling**
- Final NRG format normalization with decimal heights

## Important: Duplicate Timestamps

**WARNING**: When merging multiple files, duplicate timestamps may occur if files have overlapping time periods. The csv-merger will:

1. **Detect** all duplicate timestamps and display warnings
2. **Handle** duplicates based on the `duplicate_handling` configuration option:
   - `keep_last` (default): Keeps the last occurrence of duplicate timestamps
   - `keep_first`: Keeps the first occurrence of duplicate timestamps
   - `None`: Keeps all duplicates (not recommended)

**User Responsibility**: It is the user's responsibility to ensure timestamps only occur once in the final merged data. Review duplicate warnings carefully and:
- Verify which file contains the correct data
- Check if files have unintended overlapping periods
- Adjust the `duplicate_handling` setting if needed
- Consider manually removing problematic source files

**When using this skill**: The skill will PAUSE and warn you if duplicate timestamps are detected, requiring you to review and decide how to proceed.

## Tools Used

Located at `py-cleanmast-tools/` in project root:

- **csv-merger**: Merges multiple CSV/TXT files with timestamp normalization
- **col-name-normalizer**: Renames columns (used for both pre-merge standardization and final NRG formatting)
- **type-normalizer**: Converts string columns to float types
- **check-consistency** (planned): Detects inconsistencies across files automatically

See [py-cleanmast-tools/README.md](../py-cleanmast-tools/README.md) and [py-cleanmast-tools/docs/](../py-cleanmast-tools/docs/) for detailed tool documentation.

## Directory Structure

```
projects/{PROJECT}/
├── pre-masts/
│   ├── {MAST_ID}/
│   │   ├── {original_files}       # Raw data files (.txt, .csv, .dat)
│   │   ├── each-renamed/          # [Optional] Renamed files before merge
│   │   └── configs/
│   │       ├── rename-*.toml      # [Optional] Per-file rename configs
│   │       ├── csv-merger.toml    # Merge configuration
│   │       └── nrg-format.toml    # Final NRG normalization config
│   └── {MAST_ID}-stage/
│       └── merged.csv             # Intermediate merged file
└── masts/
    └── {MAST_ID}.csv              # Final NRG-formatted output
```

## Preprocessing Scenarios

### How to Identify Your Scenario

Before starting, inspect your data files:

```bash
# Check column headers
head -n 1 projects/{PROJECT}/pre-masts/{MAST_ID}/*.txt

# Check for differences between files
head -n 1 file1.txt file2.txt | grep -v "^$"
```

**Future**: Use `uv run check-consistency` (see [py-cleanmast-tools/TODO.md](../py-cleanmast-tools/TODO.md))

### Scenario 1: Ideal Case (Consistent Files)

**When to use**: All files have identical column names and correct types

**Tools**: csv-merger → col-name-normalizer (NRG format only)

**Example**: M2502 (single file, already consistent)

**Steps**:
1. Create `csv-merger.toml` and `nrg-format.toml`
2. Run csv-merger
3. Run col-name-normalizer for final NRG format

### Scenario 2: Column Name Inconsistencies

**When to use**: Files have different column names for same sensors
- Sensor abbreviation changes (AT→Temp, QY→Pressure)
- Height differences (7m→10m) that need standardization
- Different naming conventions across time periods

**Tools**: col-name-normalizer (per file) → csv-merger → col-name-normalizer (NRG format)

**Example**: M2501 (sensor name changes between Apr-Aug and Aug-Oct files)

**Steps**:
1. Create directory: `mkdir -p projects/{PROJECT}/pre-masts/{MAST_ID}/each-renamed`
2. Create per-file rename configs: `rename-{file}.toml`
3. Run col-name-normalizer for each file → output to `each-renamed/`
4. Create `csv-merger.toml` pointing to `each-renamed/` directory
5. Run csv-merger
6. Create `nrg-format.toml` for final NRG formatting
7. Run col-name-normalizer for final output

### Scenario 3: Type Inconsistencies

**When to use**: Numeric columns stored as strings (detected by pandas errors or inspection)

**Tools**: type-normalizer (per file) → csv-merger → col-name-normalizer (NRG format)

**Steps**:
1. Create `type-{file}.toml` for each file
2. Run type-normalizer for each file
3. Run csv-merger on type-normalized files
4. Run col-name-normalizer for final NRG format

**Note**: See [py-cleanmast-tools/docs/commands.md](../py-cleanmast-tools/docs/commands.md#type-normalizer) for type-normalizer configuration.

### Scenario 4: Combined Issues

**When to use**: Both column name and type issues present

**Tools**: type-normalizer → col-name-normalizer → csv-merger → col-name-normalizer (NRG format)

**Steps**: Combine Scenario 2 and 3 approaches - fix types first, then standardize names, merge, and apply final NRG format.

## Configuration Examples

n# Optional: Duplicate timestamp handling
# duplicate_handling = "keep_last"  # Options: "keep_first", "keep_last", or omit to keep all (default: "keep_last")
### Scenario 1: CSV Merger Config

`projects/{PROJECT}/pre-masts/{MAST_ID}/configs/csv-merger.toml`:

```toml
# CSV Merger Configuration
n# Optional: Duplicate timestamp handling
duplicate_handling = "keep_last"  # Options: "keep_first", "keep_last", or omit/set to null to keep all (default: "keep_last")

output = "../../{MAST_ID}-stage/merged.csv"

[input]
dir = ".."
delim = ","
patterns = ["*.txt"]  # or ["*.csv"], adjust as needed

[input.datetime]
format = "%Y-%m-%d %H:%M:%S"
col = "TIMESTAMP"  # or "Date & Time Stamp", adjust as needed

[input.headline]
number = 0  # Header on line 1 (0-based). Use 7 if header on line 8.
```

### Scenario 2: Per-File Column Rename Config

`projects/{PROJECT}/pre-masts/{MAST_ID}/configs/rename-{file}.toml`:

```toml
# Column renaming for individual file before merge
input_path = "../{filename}.txt"
output_path = "../each-renamed/{filename}.txt"
skip_rows = 0
header_row = 0
keep_unmapped = true
delimiter = ","

[column_mappings]
"TIMESTAMP" = "TIMESTAMP"
# Standardize sensor names
"AT_1_10m_Avg" = "Temp_1_10m_Avg"
"AT_1_10m_Std" = "Temp_1_10m_Std"
"AT_1_10m_Max" = "Temp_1_10m_Max"
"AT_1_10m_Min" = "Temp_1_10m_Min"
"QY_1_10m_Avg" = "Pressure_1_10m_Avg"
"QY_1_10m_Std" = "Pressure_1_10m_Std"
"QY_1_10m_Max" = "Pressure_1_10m_Max"
"QY_1_10m_Min" = "Pressure_1_10m_Min"
# Standardize heights
"Temp_7m_Avg" = "Temp_1_10m_Avg"
"Temp_7m_Std" = "Temp_1_10m_Std"
# ... (add other columns as needed)
```

### Final NRG Format Config (All Scenarios)

`projects/{PROJECT}/pre-masts/{MAST_ID}/configs/nrg-format.toml`:

```toml
# Column Name Normalizer Configuration - NRG Format
input_path = "../../{MAST_ID}-stage/merged.csv"
output_path = "../../../masts/{MAST_ID}.csv"
skip_rows = 0
header_row = 0
keep_unmapped = true
delimiter = ","

[column_mappings]
"Timestamp" = "Timestamp"

# Wind Speed sensors (adjust heights and channels as needed)
"WS_130m_Avg" = "Ch1_Anem_130.00m_Avg_m/s"
"WS_130m_Std" = "Ch1_Anem_130.00m_SD_m/s"
"WS_130m_Max" = "Ch1_Anem_130.00m_Max_m/s"
"WS_130m_Min" = "Ch1_Anem_130.00m_Min_m/s"

"WS_110m_Avg" = "Ch2_Anem_110.00m_Avg_m/s"
"WS_110m_Std" = "Ch2_Anem_110.00m_SD_m/s"
"WS_110m_Max" = "Ch2_Anem_110.00m_Max_m/s"
"WS_110m_Min" = "Ch2_Anem_110.00m_Min_m/s"

# Wind Direction sensors
"WD_130m_Avg" = "Ch13_Vane_130.00m_Avg_Deg"
"WD_130m_Std" = "Ch13_Vane_130.00m_SD_Deg"
"WD_130m_Max" = "Ch13_Vane_130.00m_Max_Deg"
"WD_130m_Min" = "Ch13_Vane_130.00m_Min_Deg"

# Meteorological sensors
"Temp_1_10m_Avg" = "Ch24_Temp_10.00m_Avg_C"
"Temp_1_10m_Std" = "Ch24_Temp_10.00m_SD_C"
"Temp_1_10m_Max" = "Ch24_Temp_10.00m_Max_C"
"Temp_1_10m_Min" = "Ch24_Temp_10.00m_Min_C"

"RH_1_10m_Avg" = "Ch25_RH_10.00m_Avg_%"
"RH_1_10m_Std" = "Ch25_RH_10.00m_SD_%"
"RH_1_10m_Max" = "Ch25_RH_10.00m_Max_%"
"RH_1_10m_Min" = "Ch25_RH_10.00m_Min_%"

"Pressure_1_10m_Avg" = "Ch26_Pressure_10.00m_Avg_kPa"
"Pressure_1_10m_Std" = "Ch26_Pressure_10.00m_SD_kPa"
"Pressure_1_10m_Max" = "Ch26_Pressure_10.00m_Max_kPa"
"Pressure_1_10m_Min" = "Ch26_Pressure_10.00m_Min_kPa"

# System columns
"Batt_Volt" = "Battery_V"
```

## Running the Pipeline

All commands run from `py-cleanmast-tools/` directory:

```bash
cd py-cleanmast-tools

# Scenario 1: Simple case
uv run csv-merger ../projects/{PROJECT}/pre-masts/{MAST_ID}/configs/csv-merger.toml
uv run col-name-normalizer ../projects/{PROJECT}/pre-masts/{MAST_ID}/configs/nrg-format.toml

# Scenario 2: Column name inconsistencies
# Step 1: Rename each file
uv run col-name-normalizer ../projects/{PROJECT}/pre-masts/{MAST_ID}/configs/rename-file1.toml
uv run col-name-normalizer ../projects/{PROJECT}/pre-masts/{MAST_ID}/configs/rename-file2.toml
# Step 2: Merge renamed files
uv run csv-merger ../projects/{PROJECT}/pre-masts/{MAST_ID}/configs/csv-merger.toml
# Step 3: Apply NRG format
uv run col-name-normalizer ../projects/{PROJECT}/pre-masts/{MAST_ID}/configs/nrg-format.toml

cd ..
```

## Real-World Examples

### Dulan Project (Scenario 1)

**Masts**: W2408260, W2408267
**Data characteristics**:
- 200+ daily CSV files per mast
- Consistent column names across all files
- 7 metadata rows before header

**Configuration highlights**:
- `csv-merger.toml`: `headline.number = 7` (header on line 8)
- `datetime.col = "Date & Time Stamp"`
- Direct merge → NRG format conversion

**Results**:
- W2408260: 28,984 rows from 203 files
- W2408267: 29,289 rows from 205 files

### Baiyang Project

#### M2502 (Scenario 1)

**Data characteristics**:
- Single file: `2502.txt`
- Consistent column names
- Sensor abbreviations: AT, QY (but consistent within file)

**Steps**:
1. Rename AT→Temp, QY→Pressure using col-name-normalizer
2. Merge (trivial single file case)
3. Apply NRG format

**Result**: 16,156 rows

#### M2501 (Scenario 2 - Complex)

**Data characteristics**:
- 2 files: `2501-Apr-to-Aug.txt`, `2501-Aug-to-Oct.txt`
- **Column name changes between files**:
  - File 1: `AT_1_10m_*`, `QY_1_10m_*`, `RH_1_10m_*`
  - File 2: `Temp_7m_*`, `Press_7m_*`, `RH_7m_*`
- Height standardization needed (7m → 10m for merging)

**Configuration approach**:

1. **rename-apr-aug.toml**: AT→Temp, QY→Pressure (keep 10m height)
2. **rename-aug-oct.toml**: Temp_7m→Temp_1_10m, Press_7m→Pressure_1_10m, RH_7m→RH_1_10m
3. **csv-merger.toml**: Merge from `each-renamed/` directory
4. **nrg-format.toml**: Final NRG formatting with all sensor mappings

**Key insight**: Standardize both sensor names AND heights before merging to ensure column alignment.

**Result**: 26,513 rows merged from 2 inconsistent files

**Config files**: See `projects/baiyang/pre-masts/M2501/configs/` for complete working examples.

## NRG Format Conversions

The final NRG format applies these patterns:

1. **Height Format**: `140m` → `140.00m` (2 decimal places)
2. **Wind Speed**: `WS_{height}m_{stat}` → `Ch{N}_Anem_{height}.00m_{stat}_m/s`
3. **Wind Direction**: `WD_{height}m_{stat}` → `Ch{N}_Vane_{height}.00m_{stat}_Deg` (note: `deg` → `Deg`)
4. **Temperature**: `Temp_{N}_{height}m_{stat}` → `Ch24_Temp_{height}.00m_{stat}_C`
5. **Humidity**: `RH_{N}_{height}m_{stat}` → `Ch25_RH_{height}.00m_{stat}_%`
6. **Pressure**: `Pressure_{N}_{height}m_{stat}` → `Ch26_Pressure_{height}.00m_{stat}_kPa` (note: `Kpa` → `kPa`)
7. **Battery**: `Batt_Volt` → `Battery_V`

Where:
- `{stat}` = `Avg`, `Std`, `Max`, `Min` (or `SD` for standard deviation in NRG format)
- Channel numbers (`Ch{N}`) should be consistent for each sensor type

## Tips and Troubleshooting

### Column Mapping Generation

For new masts, inspect the merged CSV header to generate mappings:

```bash
head -n 1 projects/{PROJECT}/pre-masts/{MAST_ID}-stage/merged.csv
```

Create mappings by pattern matching and adding `.00` to heights.

### Validation

Check final output has correct NRG column names:

```bash
head -n 1 projects/{PROJECT}/masts/{MAST_ID}.csv
```

### Stage Files

Keep stage files (`{MAST_ID}-stage/merged.csv`) for debugging. Remove after successful validation.

### Sensor Name Changes

If files have different sensor abbreviations (AT vs Temp, QY vs Press):
- Use Scenario 2 approach
- Create per-file rename configs
- Standardize to common names before merging
- Remember to standardize heights if they differ (7m vs 10m)

### Future: Automated Detection

The planned `check-consistency` tool will automatically detect which scenario applies. See [py-cleanmast-tools/TODO.md](../py-cleanmast-tools/TODO.md) for details.

## Data Characteristics

Standard characteristics for preprocessed data:
- **Timestamp Format**: `YYYY-MM-DD HH:MM:SS`
- **Interval**: 10-minute averages (typical)
- **Data Types**: Numeric (float64)
- **Missing Values**: Preserved through pipeline
- **Encoding**: UTF-8
