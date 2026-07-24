# song-yuan-clean

Step-wise test dataset for the **clean** pipeline step, sourced from
`projects/2026-07-02-松原-gate/` (松原 / Songyuan, 4 masts: M1664, M3142, M5057, M5972).

## Phases tested

| Phase | Recipe | What it proves |
|---|---|---|
| recommend | `recommend` + `compare-config` | `julia bin/CleanMast.jl recommend clean` regenerates the truth config |
| process | `process` + `compare-outputs` | `julia bin/CleanMast.jl process clean` reproduces truth `clean/*.parquet` |

## Layout

- `raw/` — DVC-tracked source data (8 parquet files: 4 mast + 4 ERA5)
- `formats/clean/` — git-tracked clean format configs (inputs)
- `expected/process-clean.toml` — git-tracked truth config
- `expected/clean/` — DVC-tracked truth outputs (4 parquet files)
- `clean/`, `process-clean.toml` — generated during verify; gitignored, never DVC-tracked

## Usage

```bash
just -f test-data/cleanmast/song-yuan-clean/Justfile verify
```
