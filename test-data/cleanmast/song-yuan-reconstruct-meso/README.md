# song-yuan-reconstruct-meso

Step-wise test dataset for the **reconstruct-meso** pipeline step, sourced from
`projects/2026-07-02-松原-gate/` (松原 / Songyuan, 4 masts: M1664, M3142, M5057, M5972).

This step includes an override script that patches per-mast `time_range` after
`recommend` to extend M3142/M5972 min back to 2022-08-01 (vs the cluster-optimal
2022-09-01), ensuring full coverage of the representative-year window.

## Phases tested

| Phase | Recipe | What it proves |
|---|---|---|
| recommend | `recommend` + `compare-config` | `julia bin/CleanMast.jl recommend reconstruct-meso` + override regenerates the truth config |
| process | `process` + `compare-outputs` | `julia bin/CleanMast.jl process reconstruct-meso` reproduces truth `reconstruct-meso/*.parquet` |

## Layout

- `raw/`, `reconstruct-cross/`, `meso-models/` — DVC-tracked source data (inputs)
- `just-override/` — git-tracked override script + docs (inputs)
- `expected/reconstruct-meso.toml` — git-tracked truth config (post-override)
- `expected/reconstruct-meso/` — DVC-tracked truth outputs (4 parquet files)
- `reconstruct-meso/`, `reconstruct-meso.toml` — generated during verify; gitignored, never DVC-tracked

## Usage

```bash
just -f test-data/cleanmast/song-yuan-reconstruct-meso/Justfile verify
```
