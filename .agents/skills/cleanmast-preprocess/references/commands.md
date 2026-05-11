# Preprocess Tools Command Reference

All commands are invoked via:

```bash
uv run preprocess <subcommand> path/to/config.toml
```

## csv-merge

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

## col-normalizer

```toml
input_path = "merged.csv"
output_path = "renamed.csv"
delimiter = ","
keep_unmapped = false  # REQUIRED: drop all unmapped columns

[column_mappings]
"OldName" = "NewName"
```

**Notes:**
- `keep_unmapped = false` is mandatory. Only mapped meteorological columns (plus `Timestamp`) will appear in the output. This drops empty/unnamed columns and non-meteo diagnostics automatically.
- `Timestamp` is preserved automatically (case-insensitive match: `Timestamp`, `TimeStamp`, `timestamp`, `TIMESTAMP`). Do not include it in `column_mappings`.
- The tool moves `Timestamp` to the first column position. Verify this after running.

## type-normalizer

```toml
input_path = "renamed.csv"
output_path = "final.csv"
delimiter = ","
float_columns = ["Col1", "Col2"]
```

## timestamp

```toml
input_path = "input.csv"
output_path = "output.csv"
timestamp_column = "Timestamp"
input_format = "%Y/%m/%d %H:%M:%S"
output_format = "%Y-%m-%d %H:%M:%S"
```
