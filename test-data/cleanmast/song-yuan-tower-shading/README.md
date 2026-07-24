# song-yuan-tower-shading

Step-wise test dataset for the **tower-shading** pipeline step, sourced from
`projects/2026-07-02-松原-gate/` (松原 / Songyuan, 4 masts: M1664, M3142, M5057, M5972).

## Phases tested

| Phase | Recipe | What it proves |
|---|---|---|
| recommend | `recommend` + `compare-config` | `julia bin/CleanMast.jl recommend tower-shading` regenerates the truth config |
| process | `process` + `compare-outputs` | `julia bin/CleanMast.jl process tower-shading` reproduces truth `tower-shading/*.parquet` |

## Layout

- `process-clean.toml` — git-tracked truth input (prerequisite for recommend)
- `clean/` — DVC-tracked input parquet files (4 files)
- `expected/tower-shading.toml` — git-tracked truth config
- `expected/tower-shading/` — DVC-tracked truth outputs (4 parquet files)
- `tower-shading.toml`, `tower-shading/` — generated during verify; gitignored, never DVC-tracked

## Usage

```bash
just -f test-data/cleanmast/song-yuan-tower-shading/Justfile verify
```
