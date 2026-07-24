# song-yuan-representative-year

Step-wise test dataset for the **representative-year** pipeline step, sourced from
`projects/2026-07-02-松原-gate/` (松原 / Songyuan, 4 masts: M1664, M3142, M5057, M5972).

This step has a **post-recommend override** that patches per-mast time ranges
(`just-override/override_representative_year.py`).

## Phases tested

| Phase | Recipe | What it proves |
|---|---|---|
| recommend | `recommend` + `compare-config` | `julia bin/CleanMast.jl recommend representative-year` + override regenerates the truth config |
| process | `process` + `compare-outputs` | `julia bin/CleanMast.jl process representative-year` reproduces truth `representative-year/*.parquet` |

## Layout

- `raw/` — DVC-tracked ERA5 mesoscale data (4 parquet files)
- `reconstruct-meso/` — DVC-tracked meso-reconstructed mast data (4 parquet files)
- `meso-models/` — DVC-tracked 16-sector mesoscale wind speed models (49 files)
- `just-override/` — git-tracked override script + docs
- `expected/representative-year.toml` — git-tracked truth config (post-override)
- `expected/representative-year/` — DVC-tracked truth outputs (4 parquet files)
- `representative-year/`, `representative-year.toml` — generated during verify; gitignored, never DVC-tracked

## Usage

```bash
just -f test-data/cleanmast/song-yuan-representative-year/Justfile verify
```
