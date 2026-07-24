# song-yuan-parse-sensors

Step-wise test dataset for the **parse-sensors** pipeline step, sourced from
`projects/2026-07-02-松原-gate/` (松原 / Songyuan, 4 masts: M1664, M3142, M5057, M5972).

## Phases tested

| Phase | Recipe | What it proves |
|---|---|---|
| recommend | `recommend` + `compare-config` | `julia bin/CleanMast.jl recommend parse-sensors` regenerates the truth config |
| process | `process` + `compare-outputs` | `julia bin/CleanMast.jl project parse-sensors` reproduces truth `raw/*.parquet` |

## Layout

- `masts/`, `mesos/` — DVC-tracked source data (inputs)
- `formats/` — git-tracked sensor/clean format configs (inputs)
- `expected/parse-sensors.toml` — git-tracked truth config
- `expected/raw/` — DVC-tracked truth outputs (8 parquet files)
- `raw/`, `parse-sensors.toml` — generated during verify; gitignored, never DVC-tracked

## Usage

```bash
just -f test-data/cleanmast/song-yuan-parse-sensors/Justfile verify
```
