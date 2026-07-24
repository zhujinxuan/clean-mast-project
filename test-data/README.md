# Test Data

DVC-managed real-world test datasets for CleanMast.

## Song-Yuan Step Datasets

The `song-yuan-{step}` datasets validate each CleanMast pipeline stage
against truth data from the 2026-07-02 song-yuan-gate project (4 masts:
M1664, M3142, M5057, M5972). Each step tests **recommend** (config
generation) and **process** (output generation) phases, comparing both
against gate-produced truth stored under `expected/`.

### Steps

| # | Dataset | Step |
|---|---------|------|
| 1 | `song-yuan-parse-sensors` | Parse raw logger files into parquet |
| 2 | `song-yuan-clean` | Data cleaning and QC |
| 3 | `song-yuan-tower-shading` | Tower shading detection |
| 4 | `song-yuan-reconstruct-single` | Single-mast reconstruction |
| 5 | `song-yuan-train-cross` | Cross-prediction model training |
| 6 | `song-yuan-reconstruct-cross` | Cross-prediction reconstruction |
| 7 | `song-yuan-train-meso` | Mesoscale model training |
| 8 | `song-yuan-reconstruct-meso` | Mesoscale reconstruction |
| 9 | `song-yuan-representative-year` | Representative year selection |
| 10 | `song-yuan-fill-heights` | Height filling |
| 11 | `song-yuan-wt-timeseries` | Wind turbine timeseries |
| 12 | `song-yuan-report` | Report generation |

### Layout

Each dataset mirrors the project layout:
- Input DATA files are DVC-tracked at project-relative paths
  (configs reference e.g. `masts/`, `mesos/`, `clean\*.parquet`).
- Truth outputs live under `expected/` (DVC-tracked data + git-tracked configs).
- Generated outputs at the root are **not** DVC-tracked (gitignored).
- A `Justfile` provides `pull`, `recommend`, `compare-config`, `process`,
  `compare-outputs`, `verify`, `verify-json`, and `clean` recipes.

### Usage

```bash
# Single step
just -f test-data/cleanmast/song-yuan-parse-sensors/Justfile verify

# All steps (from repo root, requires just)
uv run cleanmast verify -p cleanmast --json --jobs 4
```

## Structure

Test data is organized by package: `test-data/{packagename}/{dataset}-{command}/`

- `cleanmast/kp-202603-report/`: Test dataset for report timeseries command
  - Filled-height results from kp-202603 project
  - Two masts: L32261, M245228

## Usage

```bash
# Pull test data
dvc pull

# Run report generation
uv run cleanmast report timeseries test-data/cleanmast/kp-202603-report/rep-ts-report.toml
```

## Running Experiments

### Report Generation (`kp-202603-report`)

The report generation experiment can be run manually via the Justfile:

```bash
# Generate report from existing config
just -f test-data/cleanmast/kp-202603-report/Justfile generate-report

# Or run with PDF generation
just -f test-data/cleanmast/kp-202603-report/Justfile run-full
```

Note: DVC pipeline stages for report config validation have been temporarily removed
while the report/assessment module is under active development.

## Adding New Datasets

1. Create directory: `test-data/{packagename}/{dataset}-{command}/`
2. Copy necessary files preserving structure
3. `dvc add` each data file
4. Update this README
