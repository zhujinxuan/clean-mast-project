# song-yuan-reconstruct-cross

Step-wise test dataset for the **reconstruct-cross** pipeline step, sourced from
`projects/2026-07-02-松原-gate/` (松原 / Songyuan, 4 masts: M1664, M3142, M5057, M5972).

## Phases tested

| Phase | Recipe | What it proves |
|---|---|---|
| recommend | `recommend` + `compare-config` | `julia bin/CleanMast.jl recommend reconstruct-cross` regenerates the truth config |
| process | `process` + `compare-outputs` | `julia bin/CleanMast.jl process reconstruct-cross` reproduces truth `reconstruct-cross/*.parquet` |

## Layout

- `reconstruct-single/` — DVC-tracked input data (4 parquet files, from reconstruct-single step)
- `train-reconstruct-cross/` — DVC-tracked training models + results (cross-mast-models/ + train-results.toml)
- `expected/reconstruct-cross.toml` — git-tracked truth config
- `expected/reconstruct-cross/` — DVC-tracked truth outputs (4 parquet files + reconstruction-summary.toml)
- `reconstruct-cross/`, `reconstruct-cross.toml` — generated during verify; gitignored, never DVC-tracked

## Usage

```bash
just -f test-data/cleanmast/song-yuan-reconstruct-cross/Justfile verify
```
