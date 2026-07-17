# Archive: 松原

- **Source experiment**: `projects/2026-07-02-松原/`
- **Archive date**: 2026-07-13
- **Archive policy**: DVC plaintext files compressed into `.tar.zst` per
  directory. Parquet files tracked individually. Git-tracked files (.toml,
  .json, .yaml, .yml, .md, .py, justfile.archive) committed directly.
  The original project's Justfile is stored PRISTINE as `justfile.archive`;
  `deploy.py` restores the experiment to a target directory.

## DVC-Tracked Archives

| Archive File | Original Directory | Contents |
|---|---|---|
| `masts.tar.zst` | `masts/` | 4 mast CSV sensor files: M1664, M3142, M5057, M5972 |
| `mesos.tar.zst` | `mesos/` | 4 ERA5 mesoscale text files: ERA5M1664, ERA5M3142, ERA5M5057, ERA5M5972 |
| `pre-masts/raw.tar.zst` | `pre-masts/raw/` | 4 raw mast text files: M1664, M3142, M5057, M5972 |
| `pre-masts/preprocessed/M1664.tar.zst` | `pre-masts/preprocessed/M1664/` | Preprocessed CSV files + UTF-8 text for M1664 |
| `pre-masts/preprocessed/M3142.tar.zst` | `pre-masts/preprocessed/M3142/` | Preprocessed CSV files for M3142 |
| `pre-masts/preprocessed/M5057.tar.zst` | `pre-masts/preprocessed/M5057/` | Preprocessed CSV files + UTF-8 text for M5057 |
| `pre-masts/preprocessed/M5972.tar.zst` | `pre-masts/preprocessed/M5972/` | Preprocessed CSV files for M5972 |

## DVC-Tracked Individual Files

| File | Size | Description |
|---|---|---|
| `raw/ERA5M1664.parquet` | 6.8 MB | ERA5 mesoscale parsed data for M1664 |
| `raw/ERA5M3142.parquet` | 6.8 MB | ERA5 mesoscale parsed data for M3142 |
| `raw/ERA5M5057.parquet` | 6.8 MB | ERA5 mesoscale parsed data for M5057 |
| `raw/ERA5M5972.parquet` | 6.8 MB | ERA5 mesoscale parsed data for M5972 |
| `raw/M1664.parquet` | 21.3 MB | Mast sensor parsed data for M1664 |
| `raw/M3142.parquet` | 11.6 MB | Mast sensor parsed data for M3142 |
| `raw/M5057.parquet` | 19.0 MB | Mast sensor parsed data for M5057 |
| `raw/M5972.parquet` | 12.0 MB | Mast sensor parsed data for M5972 |

## Git-Tracked Files

- `justfile.archive` (pristine copy of the original project's Justfile)
- `deploy.py` (deploy/restore script — see below)
- `parse-sensors.toml`
- `formats/sensor/freemeso-meso.toml`
- `formats/sensor/gangbei-231013.toml`
- `formats/sensor/gt.toml`
- `formats/sensor/lidar.toml`
- `formats/sensor/nrg-rwd.toml`
- `formats/sensor/nrg.toml`
- `formats/clean/default.toml`
- `formats/clean/lidar-availability.toml`
- `formats/clean/nrg-guideline.toml`
- `formats/clean/nrg-strict.toml`
- `masts/README.md`
- `mesos/README.md`
- `pre-masts/README.md`
- `pre-masts/preprocessed/postprocess_clean.py`
- `pre-masts/preprocessed/VALIDATION.md`
- `pre-masts/preprocessed/M1664/01_csv_merge.toml`
- `pre-masts/preprocessed/M1664/02_col_normalize.toml`
- `pre-masts/preprocessed/M1664/03_type_normalize.toml`
- `pre-masts/preprocessed/M1664/evidence.md`
- `pre-masts/preprocessed/M3142/01_csv_merge.toml`
- `pre-masts/preprocessed/M3142/02_col_normalize.toml`
- `pre-masts/preprocessed/M3142/03_type_normalize.toml`
- `pre-masts/preprocessed/M3142/evidence.md`
- `pre-masts/preprocessed/M5057/01_csv_merge.toml`
- `pre-masts/preprocessed/M5057/02_col_normalize.toml`
- `pre-masts/preprocessed/M5057/03_type_normalize.toml`
- `pre-masts/preprocessed/M5057/evidence.md`
- `pre-masts/preprocessed/M5972/01_csv_merge.toml`
- `pre-masts/preprocessed/M5972/02_col_normalize.toml`
- `pre-masts/preprocessed/M5972/03_type_normalize.toml`
- `pre-masts/preprocessed/M5972/evidence.md`
- `just-override/override-representative-year.md`
- `just-override/override_representative_year.py`

## Deploy (Restore for Replay)

```bash
# From the repository root. Restores DVC data, extracts archives, copies
# the payload to the target, renames justfile.archive -> Justfile, and
# strips read-only attributes so pipeline steps can rewrite raw/*.parquet.
# The deployed directory is NOT DVC-tracked.
uv run python experiments-archived/2026-07-13-松原/deploy.py projects/<new-project-name>
```

For raw data access without deploying: `dvc pull -R experiments-archived/2026-07-13-松原/`,
then extract each `.tar.zst` from the directory containing it.
