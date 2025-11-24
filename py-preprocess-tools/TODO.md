# py-preprocess-tools TODO

## Column Consistency Checker

### Purpose
Tool to analyze multiple data files under one mast and detect inconsistencies before merging.

### Problem Statement
When preprocessing mast data, files may have:
- Different column names for the same sensor (e.g., `AT_1_10m_Avg` vs `Temp_1_10m_Avg`)
- Different heights for the same sensor type (e.g., `Temp_7m_Avg` vs `Temp_10m_Avg`)
- Type mismatches where numeric data is stored as strings
- Inconsistent column presence across time periods

Currently, users must manually inspect file headers to detect these issues.

### Features
- Scan all files in a directory (by pattern, e.g., `*.txt`, `*.csv`)
- Compare column names across files
- Detect type mismatches (string vs numeric for same column name)
- Report differences clearly with file-by-file breakdown
- Suggest which preprocessing scenario applies (Scenario 1/2/3/4)
- Optionally generate skeleton configs for detected scenario

### Output Format

```
Column Consistency Report
========================
Directory: projects/baiyang/pre-masts/M2501/
Files analyzed: 2

File 1: 2501-Apr-to-Aug.txt (59 columns)
File 2: 2501-Aug-to-Oct.txt (59 columns)

Column Name Differences:
  File 1 only:
    - AT_1_10m_Avg, AT_1_10m_Std, AT_1_10m_Max, AT_1_10m_Min
    - QY_1_10m_Avg, QY_1_10m_Std, QY_1_10m_Max, QY_1_10m_Min
    - RH_1_10m_Avg, RH_1_10m_Std, RH_1_10m_Max, RH_1_10m_Min

  File 2 only:
    - Temp_7m_Avg, Temp_7m_Std, Temp_7m_Max, Temp_7m_Min
    - Press_7m_Avg, Press_7m_Std, Press_7m_Max, Press_7m_Min
    - RH_7m_Avg, RH_7m_Std, RH_7m_Max, RH_7m_Min

Type Mismatches:
  None detected

Recommendation:
  → Scenario 2: Column Name Inconsistencies
  → Use col-name-normalizer to standardize column names before merging
  → Consider height standardization (7m → 10m) for merging
```

### Usage (planned)

```bash
cd py-preprocess-tools

# Basic consistency check
uv run check-consistency ../projects/{PROJECT}/pre-masts/{MAST_ID}/

# With file pattern
uv run check-consistency ../projects/{PROJECT}/pre-masts/{MAST_ID}/ --pattern "*.txt"

# Generate skeleton configs for detected scenario
uv run check-consistency ../projects/{PROJECT}/pre-masts/{MAST_ID}/ --generate-configs
```

### Implementation Notes

#### Technology
- Use pandas to read headers and infer types
- Support delimiter detection (`,` vs `\t`)
- Handle metadata rows (skip_rows configuration)

#### Comparison Logic
1. Read first N rows of each file to infer schema
2. Extract column names and dtypes
3. Build comparison matrix showing:
   - Common columns (present in all files)
   - File-specific columns (appear/disappear)
   - Type differences for common columns
4. Suggest scenario based on detected patterns

#### Config Generation
If `--generate-configs` is used and Scenario 2/3/4 detected:
- Generate `rename-{file}.toml` for each file with column differences
- Generate `csv-merger.toml` template
- Generate `nrg-format.toml` template

#### Edge Cases
- Files with different delimiters
- Files with different metadata row counts
- Binary files or corrupted data
- Very large files (sample first 1000 rows only)

### Future Enhancements
- Auto-detect common sensor name patterns and suggest mappings
- Validate against NRG format requirements
- Detect timestamp format inconsistencies
- Integration with csv-merger to auto-fix simple cases
- Support for recursive directory scanning (multiple masts)
