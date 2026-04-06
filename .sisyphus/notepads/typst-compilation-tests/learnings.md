# Learnings from Typst Compilation Tests

## Schema Requirements
- WindRoseSchema requires `month` and `month_name` columns in addition to sector, height, frequency, etc.
- The existing `sample_wind_rose_df` fixture was missing these columns and had to be updated

## Snapshot Management
- Snapshots should be regenerated when fixture data changes
- Malformed snapshots (with incorrect comma placement) need to be fixed
- The `compare_with_snapshot` method skips if snapshot doesn't exist

## Test Pattern
- Follow existing test pattern: renderTable() -> compare_with_snapshot() -> compile_typst() -> assert
- Use tmp_path for PDF output files
- Check both success flag and output file existence

## Typst Syntax Requirements
- Table rows must have trailing commas
- Content inside brackets should not have additional brackets (avoid `[[label]]`)
- UTF-8 encoding is required for Chinese characters
