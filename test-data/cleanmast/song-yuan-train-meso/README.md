# song-yuan-train-meso

Step-wise test dataset for the **train-meso** pipeline step, sourced from
`projects/2026-07-02-松原-gate/` (松原 / Songyuan, 4 masts: M1664, M3142, M5057, M5972).

## Phases tested

| Phase | Recipe | What it proves |
|---|---|---|
| recommend | `recommend` + `compare-config` | `julia bin/CleanMast.jl recommend train-meso` regenerates the truth config |
| process | `process` + `compare-outputs` | `julia bin/CleanMast.jl process train-meso` reproduces truth `meso-models/` |

## Layout

- `raw/`, `tower-shading/` — DVC-tracked source data (8 parquet files, inputs)
- `expected/train-meso.toml` — git-tracked truth config
- `expected/meso-models/` — DVC-tracked truth outputs (48 jld2 models + train-meso-results.toml)
- `train-meso.toml`, `meso-models/`, `logs/` — generated during verify; gitignored, never DVC-tracked

## Usage

```bash
just -f test-data/cleanmast/song-yuan-train-meso/Justfile verify
```
