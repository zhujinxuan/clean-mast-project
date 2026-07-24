# song-yuan-fill-heights

Step-wise test dataset for the **fill-heights** pipeline step, sourced from
`projects/2026-07-02-松原-gate/` (松原 / Songyuan, 4 masts: M1664, M3142, M5057, M5972).

## Phases tested

| Phase | Recipe | What it proves |
|---|---|---|
| recommend | `recommend` + `compare-config` | `uv run cleanmast recommend fill-heights` regenerates both truth configs (reconstruct-meso + representative-year) |
| process | `process` + `compare-outputs` | `uv run cleanmast fill-heights` reproduces truth `reconstruct-meso-fill-heights/*.parquet` and `representative-year-fill-heights/*.parquet` |

## Layout

- `reconstruct-meso.toml`, `representative-year.toml` — git-tracked input configs (needed for config discovery during recommend)
- `reconstruct-meso/`, `representative-year/` — DVC-tracked input parquet data
- `expected/fill-heights-reconstruct-meso.toml`, `expected/fill-heights-representative-year.toml` — git-tracked truth configs
- `expected/fill-models/` — DVC-tracked truth trained models
- `expected/reconstruct-meso-fill-heights/`, `expected/representative-year-fill-heights/` — DVC-tracked truth outputs (4 parquets + 4 sensors.yaml each)
- `fill-heights-*.toml`, `reconstruct-meso-fill-heights/`, `representative-year-fill-heights/`, `fill-models/` — generated during verify; gitignored, never DVC-tracked

## Usage

```bash
just -f test-data/cleanmast/song-yuan-fill-heights/Justfile verify
```
