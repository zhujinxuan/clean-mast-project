---
name: cleanmast-preprocess
description: |
  Guide for preprocessing raw wind meteorological mast data using CleanMast's preprocess-tools package.
  MUST USE this skill whenever the user mentions preprocessing wind mast data, NRG logger files,
  Lidar data, CSV merging for wind data, normalizing column names for mast sensors, or converting
  raw wind measurement files. Also trigger when the user asks to merge multiple .txt/.csv/.dat
  wind data files, fix timestamp formats in mast data, or handle column mismatches across logger
  export files.
---

# CleanMast Preprocessing Skill

This skill guides the step-by-step preprocessing of raw wind mast / Lidar data using the
`preprocess-tools` package in the CleanMast workspace.

## Quick Workflow

Typical preprocessing pipeline for raw logger files:

1. **csv-merge** — Merge multiple raw files, normalize timestamps, handle duplicates
2. **col-normalizer** — Rename columns to standard NRG or Lidar formats
3. **type-normalizer** — Convert string columns to Float64
4. **timestamp** — (If needed) Reformat timestamp columns

## Before You Start

Always inspect the raw data first:
- What file format? (`.txt`, `.csv`, `.dat`, `.wnd`)
- What delimiter? (tab, comma, semicolon)
- Where is the header line? (0-based line number, or use regex)
- What is the datetime format? (`%Y/%m/%d %H:%M:%S`, `%Y-%m-%d %H:%M`, etc.)
- Is the datetime in one column or separate date/time columns?

Use `head -20 <file>` or read the first few lines to determine this.

## Running the Tools

All tools are available via:

```bash
uv run preprocess <subcommand> <config.toml>
```

Subcommands: `csv-merge`, `col-normalizer`, `type-normalizer`, `timestamp`

For detailed config options, read `@references/commands.md`.

## Common Patterns

### NRG SDR .txt files

NRG Symphonie Data Retriever files usually have:
- Tab delimiter (`\t`)
- Header on line ~170 (0-based)
- Datetime column named `Date & Time Stamp`
- Format `%Y/%m/%d %H:%M:%S`

Example csv-merge config:

```toml
output = "merged.csv"
duplicate_handling = "keep_last"
column_mismatch = "union"

[input]
dir = "./raw"
delim = "\t"
patterns = ["*.txt"]

[input.datetime]
col = "Date & Time Stamp"
format = "%Y/%m/%d %H:%M:%S"

[input.headline]
number = 170
```

**Column mismatches**: Real-world NRG exports often vary slightly (e.g. `CH13_Custom_Avg` vs `CH13_NRG_40C_Anem_ms_Avg`). Always set `column_mismatch = "union"` when merging multiple NRG files so the merger combines all columns and fills missing values with null.

### Post-Merge Cleanup: Drop Empty/Unnamed Columns

After `csv-merge`, inspect the merged CSV for artifacts:

```bash
uv run python -c "
import polars as pl
df = pl.read_csv('merged.csv', infer_schema_length=0)
print(f'Total columns: {len(df.columns)}')
bad = [c for c in df.columns if c == '' or c.strip() == '' or c.startswith('_duplicated_')]
print(f'Empty/unnamed columns: {len(bad)}')
for c in bad:
    print(f'  {repr(c)}')
"
```

If empty/unnamed columns exist, drop them before column normalization:

```bash
uv run python -c "
import polars as pl
df = pl.read_csv('merged.csv')
# Drop empty/unnamed columns
good_cols = [c for c in df.columns if c != '' and not c.startswith('_duplicated_')]
df = df.select(good_cols)
df.write_csv('merged_cleaned.csv')
print(f'Dropped {len(df.columns) - len(good_cols)} empty columns')
"
```

Common causes of empty columns:
- Trailing delimiters in raw data (e.g. Lidar CSV exports ending with `,,`)
- Merging files with mismatched column counts
- Custom merge scripts that concatenate sections with trailing commas

**Always run this check after merging.** Empty columns will break downstream tools.

### Column Name Normalization

After merging and cleanup, use `col-normalizer` to map raw column names to the standard NRG format.

See `@references/nrg-format.md` for the exact naming convention (`Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}`).

Create a TOML config with explicit `column_mappings`:

```toml
input_path = "merged_cleaned.csv"
output_path = "normalized.csv"
delimiter = ","
keep_unmapped = false  # REQUIRED: drop all unmapped columns

[column_mappings]
"CH1_NRG_40C_Anem_80m_Avg" = "Ch1_Anem_80.00m_A_Avg_m/s"
"CH7_NRG_200P_Vane_80m_Avg" = "Ch7_Vane_80.00m_A_Avg_Deg"
```

**`keep_unmapped = false` is mandatory.** This ensures only meteorological sensors are kept in the final dataset. The col-normalizer will drop:
- Empty/unnamed columns (`''`, `_duplicated_N`)
- Non-meteorological diagnostics (battery voltage, logger status, custom placeholders)
- Any column not explicitly mapped in `column_mappings`

Verify the output columns match exactly your mapping keys (plus `Timestamp`).

**Important:** The `col-normalizer` automatically preserves `Timestamp` (case-insensitive) even when `keep_unmapped = false`. It also moves `Timestamp` to the first column. Do **not** include `Timestamp` in your `column_mappings`.

#### Verify `Timestamp` is preserved

After running `col-normalizer`, confirm the output contains `Timestamp` as the first column:

```bash
uv run python -c "
import polars as pl
df = pl.read_csv('normalized.csv', infer_schema_length=0)
print(f'First column: {repr(df.columns[0])}')
print(f'Columns: {len(df.columns)}')
assert df.columns[0] == 'Timestamp', 'Timestamp must be first column'
print('OK: Timestamp preserved and in first position')
"
```

If this fails, the input `merged.csv` may not have a recognizable timestamp column. Check that `csv-merge` produced a column named `Timestamp` (exact case).

#### Document your decisions in `evidence.md`

Before running `col-normalizer`, write an `evidence.md` file in the same directory as your config. This is mandatory — it captures the rationale for every channel decision and makes evaluation failures debuggable.

**Required format** (markdown table):

```markdown
| Channel | Raw Column | Mapped Column | Height Source | Rationale |
|---|---|---|---|---|
| CH1 | CH1_NRG_40C_Anem_80m_Avg | Ch1_Anem_80.00m_Avg_m/s | Column name | Height 80m parsed directly from header |
| CH9 | CH9_NRG_110S_Temp_C_Avg | Ch9_Analog_10.00m_Avg_C | Metaheader | Column omits height; metaheader confirms 10m |
| CH13 | CH13_NRG_40C_Anem_ms_Avg | Ch13_Anem_0.00m_Avg_m/s | Fallback 0.00m | No height in column; metaheader is 0/empty → info missing |
| CH12 | CH12_iPack_Voltmtr_volts_Avg | DROPPED | N/A | Non-meteo diagnostic (battery voltage) |
```

Rules for `evidence.md`:
- Every **kept** meteorological column must have a row.
- Every **dropped** non-meteo column must have a row with `DROPPED` in the Mapped Column.
- `Height Source` must be one of: `Column name`, `Metaheader`, `Fallback 0.00m`, `N/A`.
- `Rationale` should be one sentence explaining how you applied `@references/checklist.md`.

See `@references/evidence.md` for a complete reference example from the M4941 dataset.

### Type Normalization

After column normalization, ensure numeric columns are Float64:

```toml
input_path = "normalized.csv"
output_path = "final.csv"
float_columns = [
  "Ch1_Anem_80.00m_Avg_m/s",
  "Ch7_Vane_80.00m_Avg_Deg",
]
```

## Post-Preprocessing Sensitivity Check

After `type-normalizer`, always run a manual sanity check on the final dataset before passing it to downstream analysis. `preprocess-tools` does **not** perform meteorological validation — that responsibility currently lies with the user during preprocessing.

### Quick summary command

Run a quick summary on `_Avg` columns to flag physically implausible values:

```bash
uv run python -c "
import polars as pl
df = pl.read_csv('final.csv')
avg_cols = [c for c in df.columns if '_Avg_' in c]
for col in avg_cols:
    print(f'{col}: min={df[col].min():.3f}, mean={df[col].mean():.3f}, max={df[col].max():.3f}, nulls={df[col].null_count()}')
"
```

### 1. Mean / range checks by sensor type

Use the following reference ranges (derived from CleanMast default clean configs and typical ambient limits) to judge whether averages look sensible:

| Sensor Type | Typical Min | Typical Max | Notes |
|---|---|---|---|
| `Anem` (wind speed) | `0.0` | `30.0` m/s | Downstream clean config uses 0–30. Extreme sites may legitimately exceed 30. |
| `Vane` (wind direction) | `0.0` | `360.0` deg | Circular; values outside this range indicate scaling or unit errors. |
| `Analog` temperature | `-40.0` | `+50.0` °C | Ambient range. Values stuck at exact logger offsets (e.g., `-86.383`) indicate sensor failure. |
| `Analog` pressure | `80.0` | `110.0` kPa | Sea-level ~101.3 kPa; decreases with elevation. |

**If values fall outside these ranges, investigate before proceeding.** Common causes:
- Logger offset values replacing missing data (e.g., `-86.383` for temperature when the metaheader offset is `-86.383`).
- Unit confusion (e.g., hPa vs kPa for pressure).
- Column mis-mapping (e.g., a diagnostic channel accidentally mapped as meteorological).

### 2. Negative counts where physically impossible

Wind speed and wind direction averages should **never** be negative:

```python
neg_speed = [c for c in df.columns if 'Anem' in c and df[c].min() < 0]
neg_dir   = [c for c in df.columns if 'Vane' in c and df[c].min() < 0]
```

If any are found, the column mapping or source file likely contains an error.

### 3. Stuck / constant sensors

Check for long periods where `min == max`, especially at suspicious values:

```python
# Example: count rows where temperature equals the logger offset exactly
stuck_count = df.filter(pl.col('Ch9_Analog_10.00m_Avg_C') == -86.383).shape[0]
```

A high stuck-count relative to total rows suggests the sensor was disconnected, frozen, or malfunctioning.

### 4. Zero-height (`0.00m`) sensors

Any column with `0.00m` in its name was mapped using the **fallback height** because neither the column header nor the metaheader provided a real height. This is **not** a data error, but it is a metadata gap.

**You must decide:**
- **Keep** the column if you will supply the correct height later in the analysis config.
- **Drop** the column if the sensor is not needed for analysis.
- **Re-process** if you can find the true height from the site logger configuration sheet.

Document your decision in `evidence.md`.

### How to document findings

Do not silently fix data. If you find unsensible values or zero-height sensors, add a **Findings** subsection to `evidence.md`:

```markdown
## Preprocessing Findings

| Column | Issue | User Decision | Rationale |
|---|---|---|---|
| Ch9_Analog_10.00m_Avg_C | 2,412 rows stuck at -86.383C (logger offset) | Mark as missing/null | Temperature sensor failure; offset value is not real data |
| Ch13_Anem_0.00m_Avg_m/s | Height fallback 0.00m | Keep with note | Height unknown; will configure in analysis TOML later |
```

This creates an audit trail and prevents downstream analysis from silently using bad data.

## Lessons Learned (Read Before Mapping)

These are real-world pitfalls discovered while preprocessing NRG logger exports. Do not assume the raw column names are consistent or fully descriptive.

### 1. Column names vary across files in the same dataset
Real-world NRG Symphonie exports often have inconsistent column names. For example, some files in the same mast may contain `CH13_Custom_Avg` while others contain `CH13_NRG_40C_Anem_ms_Avg`. If you do not handle this, `csv-merge` will fail with a column mismatch error. **Always set `column_mismatch = "union"`** when merging multiple NRG files so the merger combines all columns and fills missing values with null.

### 2. Non-meteorological diagnostic columns are present
NRG logger files often include non-meteo diagnostics that must be removed:
- `CH*_No_SCM_Installed_*` (SIM card / logger status)
- `CH*_iPack_Voltmtr_volts_*` (battery voltage)
- `CH*_Custom_*` (custom/logger diagnostic placeholders)

**Do not keep these in the final dataset.** Use `col-normalizer` with `keep_unmapped = false` and map **only** the true meteorological sensors. Verify with `@references/checklist.md` after merging.

### 3. Sensor height resolution hierarchy
When determining the correct height for a channel, follow this order of precedence:

1. **Tabular column header first** — If the column name includes the height (e.g. `CH1_NRG_40C_Anem_80m_Avg`), use that value. It is the most reliable source for CH1–CH8.
2. **NRG metaheaders second** — If the column name omits the height, inspect the per-channel metaheader block above the data header. Look for `Height\tX` under the matching `Channel #`.
3. **Fallback to `0.00m`** — If **both** the column name and the metaheader lack a real height value, use `0.00m` in the mapped header. This means "height information is missing," not necessarily that the sensor is at ground level.

**Important**: `Height\t0` in NRG metaheaders usually means "not configured" rather than "physically at 0m." For example, in the M4941 dataset CH13–CH15 show `Height\t0` in the very first file and an empty `Height\tm` in all subsequent files, confirming the height was never properly entered into the logger. Only use `0.00m` when you have confirmed that both the column name and the metaheader provide no usable height.

Example metaheader inspection:
```bash
head -n 170 file.txt | grep -A 6 "Channel #\t13"
```

### 4. Temperature height is independent of anemometer height
Do not assume the temperature sensor is at the same height as the top anemometer. In the M4941 dataset, `CH9_NRG_110S_Temp_C_Avg` is at 10m, not 80m. Always verify the sensor mount height from the site configuration.

### 5. `keep_unmapped = false` is mandatory
Always set `keep_unmapped = false` in the col-normalizer config. This is the only way to ensure the final dataset contains **only** meteorological sensors. The col-normalizer will automatically drop:
- Empty/unnamed columns (`''`, `_duplicated_N`)
- Non-meteorological diagnostics
- Any column not explicitly mapped

Verify the output columns match exactly your mapping keys (plus `Timestamp`).

## Error Handling Guidelines

- **Column mismatch during merge**: Set `column_mismatch = "union"` in the csv-merge config.
- **Header not found**: Double-check the 0-based line number. Use `grep -n "^Date" <file>` to find it.
- **Encoding issues**: The csv-merger auto-detects encoding. If it fails, convert manually with `iconv`.
- **Type conversion fails**: Check for non-numeric sentinel values (e.g. `-999`, `NaN`, empty strings) and clean them before type-normalizer.

## References

- `@references/commands.md` — Full command and config reference for all four tools
- `@references/nrg-format.md` — Standard NRG column naming conventions
- `@references/checklist.md` — Post-merge self-check checklist
- `@references/eval-setup.md` — How to add a new evaluation experiment (DVC, outputs, cleanup)
