# Archive: source-experiment

- **Source experiment**: `temp/archive-skill-test/source-experiment/`
- **Archive date**: 2026-07-13
- **Archive policy**: DVC plaintext files compressed into `.tar.zst` per
  directory. Parquet files tracked individually. Git-tracked files (.toml,
  .json, .yaml, .yml, .md, .py, Justfile) committed directly.

## DVC-Tracked Archives

| Archive File | Original Directory | Contents |
|---|---|---|
| `masts.tar.zst` | `masts/` | Mast CSV measurement data (M1664, M3142, M5057, M5972) |
| `mesos.tar.zst` | `mesos/` | ERA5 mesoscale wind data text files |
| `pre-masts/raw.tar.zst` | `pre-masts/raw/` | Raw mast logger TXT exports |
| `pre-masts/preprocessed/M1664.tar.zst` | `pre-masts/preprocessed/M1664/` | Preprocessed mast M1664 (merged, cleaned, normalized, final CSVs + UTF-8 TXT) |
| `pre-masts/preprocessed/M3142.tar.zst` | `pre-masts/preprocessed/M3142/` | Preprocessed mast M3142 (merged, cleaned, normalized, final CSVs) |
| `pre-masts/preprocessed/M5057.tar.zst` | `pre-masts/preprocessed/M5057/` | Preprocessed mast M5057 (merged, cleaned, normalized, final CSVs + UTF-8 TXT) |
| `pre-masts/preprocessed/M5972.tar.zst` | `pre-masts/preprocessed/M5972/` | Preprocessed mast M5972 (merged, cleaned, normalized, final CSVs) |

## DVC-Tracked Individual Files

| File | Size | Description |
|---|---|---|
| `raw/ERA5M1664.parquet` | 6.8 MB | ERA5 mesoscale data for M1664 |
| `raw/ERA5M3142.parquet` | 6.8 MB | ERA5 mesoscale data for M3142 |
| `raw/ERA5M5057.parquet` | 6.8 MB | ERA5 mesoscale data for M5057 |
| `raw/ERA5M5972.parquet` | 6.8 MB | ERA5 mesoscale data for M5972 |
| `raw/M1664.parquet` | 21.3 MB | Raw mast measurements for M1664 |
| `raw/M3142.parquet` | 11.6 MB | Raw mast measurements for M3142 |
| `raw/M5057.parquet` | 19.0 MB | Raw mast measurements for M5057 |
| `raw/M5972.parquet` | 12.0 MB | Raw mast measurements for M5972 |

## Git-Tracked Files

- `Justfile`
- `parse-sensors.toml`
- `just-override/override_representative_year.py`
- `just-override/override-representative-year.md`
- `masts/README.md`
- `mesos/README.md`
- `pre-masts/README.md`
- `pre-masts/preprocessed/postprocess_clean.py`
- `pre-masts/preprocessed/VALIDATION.md`
- `pre-masts/preprocessed/M1664/evidence.md`
- `pre-masts/preprocessed/M1664/01_csv_merge.toml`
- `pre-masts/preprocessed/M1664/02_col_normalize.toml`
- `pre-masts/preprocessed/M1664/03_type_normalize.toml`
- `pre-masts/preprocessed/M3142/evidence.md`
- `pre-masts/preprocessed/M3142/01_csv_merge.toml`
- `pre-masts/preprocessed/M3142/02_col_normalize.toml`
- `pre-masts/preprocessed/M3142/03_type_normalize.toml`
- `pre-masts/preprocessed/M5057/evidence.md`
- `pre-masts/preprocessed/M5057/01_csv_merge.toml`
- `pre-masts/preprocessed/M5057/02_col_normalize.toml`
- `pre-masts/preprocessed/M5057/03_type_normalize.toml`
- `pre-masts/preprocessed/M5972/evidence.md`
- `pre-masts/preprocessed/M5972/01_csv_merge.toml`
- `pre-masts/preprocessed/M5972/02_col_normalize.toml`
- `pre-masts/preprocessed/M5972/03_type_normalize.toml`

## Pull Instructions

```bash
# Clone the repo and pull DVC data for this archive
git clone <repo-url>
cd <repo-name>
dvc pull -R experiments-archived/2026-07-13-source-experiment/

# Extract all archives
just -f experiments-archived/2026-07-13-source-experiment/Justfile pull
```
