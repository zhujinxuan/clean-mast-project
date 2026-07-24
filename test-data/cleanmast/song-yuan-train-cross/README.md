# song-yuan-train-cross

Step-wise test dataset for the **train-cross** pipeline step, sourced from
`projects/2026-07-02-松原-gate/` (松原 / Songyuan, 4 masts: M1664, M3142, M5057, M5972).

## Phases tested

| Phase | Recipe | What it proves |
|---|---|---|
| recommend | `recommend` + `compare-config` | `julia bin/CleanMast.jl recommend train-reconstruct-cross` regenerates the truth config |

Note: The process phase (cross-mast model training) is not exercised in CI due to runtime.
Output comparison is skipped because this step produces `.jld2` model files and
`train-results.toml`, not `.parquet` files.

## Layout

- `reconstruct-single.toml` — git-tracked config (needed by recommend to discover masts and data paths)
- `reconstruct-single/` — DVC-tracked source data (inputs, 4 parquet files)
- `expected/train-reconstruct-cross.toml` — git-tracked truth config
- `expected/train-reconstruct-cross/` — DVC-tracked truth outputs (cross-mast-models/ + train-results.toml)
- `train-reconstruct-cross.toml`, `train-reconstruct-cross/` — generated during verify; gitignored, never DVC-tracked

## Usage

```bash
just -f test-data/cleanmast/song-yuan-train-cross/Justfile verify
```
