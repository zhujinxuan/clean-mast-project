# song-yuan-wt-timeseries

Step-wise test dataset for the **wt-timeseries** pipeline step, sourced from
`projects/2026-07-02-松原-gate/` (松原 / Songyuan, 4 masts: M1664, M3142, M5057, M5972).

## Phases tested

| Phase | Recipe | What it proves |
|---|---|---|
| recommend | `recommend` + `compare-config` | `uv run cleanmast recommend wt-timeseries` regenerates the truth config |
| process | `process` + `compare-outputs` | `uv run cleanmast wt-timeseries` reproduces truth `wt-timeseries/*.csv` + turbulence dirs |

## Layout

- `representative-year-fill-heights/` — DVC-tracked input parquet data (4 files)
- `expected/wt-timeseries.toml` — git-tracked truth config
- `expected/wt-timeseries/` — DVC-tracked truth outputs (4 CSVs + 4 turbulence-* dirs)
- `wt-timeseries/`, `wt-timeseries.toml` — generated during verify; gitignored, never DVC-tracked

## Usage

```bash
just -f test-data/cleanmast/song-yuan-wt-timeseries/Justfile verify
```
