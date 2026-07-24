# song-yuan-report

Step-wise test dataset for the **report-timeseries** pipeline step, sourced from
`projects/2026-07-02-松原-gate/` (松原 / Songyuan, 4 masts: M1664, M3142, M5057, M5972).

- **Purpose**: Generate wind resource timeseries report (PDF/DOCX) from filled-height mast data.

## Phases tested

| Phase | Recipe | What it proves |
|---|---|---|
| recommend | `recommend` + `compare-config` | `uv run cleanmast recommend report-configs timeseries` regenerates the truth config |
| process | `process` (CI only) | `uv run cleanmast report timeseries` produces `rep-ts/report.pdf` |

## Layout

- `raw/`, `reconstruct-meso-fill-heights/`, `representative-year-fill-heights/`, `reconstruct-meso/` — DVC-tracked input data (16 parquet files)
- `expected/rep-ts-report.toml` — git-tracked truth config
- `rep-ts/`, `rep-ts-report.toml` — generated during verify; gitignored, never DVC-tracked

## Usage

```bash
just -f test-data/cleanmast/song-yuan-report/Justfile recommend compare-config
```
