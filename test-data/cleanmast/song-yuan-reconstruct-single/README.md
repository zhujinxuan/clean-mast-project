# song-yuan-reconstruct-single

Step-wise test dataset for the **reconstruct-single** pipeline step, sourced from
`projects/2026-07-02-松原-gate/` (松原 / Songyuan, 4 masts: M1664, M3142, M5057, M5972).

## Phases tested

| Phase | Recipe | What it proves |
|---|---|---|
| recommend | `recommend` + `compare-config` | `julia bin/CleanMast.jl recommend reconstruct-single` regenerates the truth config |
| process | `process` + `compare-outputs` | `julia bin/CleanMast.jl process reconstruct-single` reproduces truth `reconstruct-single/*.parquet` |

## Layout

- `tower-shading/` — DVC-tracked source data (inputs from tower-shading step)
- `tower-shading.toml` — git-tracked tower-shading config (input for recommend)
- `expected/reconstruct-single.toml` — git-tracked truth config
- `expected/reconstruct-single/` — DVC-tracked truth outputs (4 parquet files)
- `reconstruct-single/`, `reconstruct-single.toml` — generated during verify; gitignored, never DVC-tracked

## Usage

```bash
just -f test-data/cleanmast/song-yuan-reconstruct-single/Justfile verify
```
