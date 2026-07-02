---
name: run-experiment
description: |
  Run a CleanMast wind energy experiment from preprocessed mast/meso data.
  Use after preprocessing raw logger files via cleanmast-preprocess.
  Trigger on: "run experiment", "run pipeline", "just run-all",
  "process masts", "generate report", "execute cleanmast pipeline",
  or when the user has data in masts/ and mesos/ directories.
---

# Run Experiment Skill

This skill runs the CleanMast Julia + Python pipeline after raw mast data
has been preprocessed into `masts/` and `mesos/` directories.

## Prerequisites

Check these before running:

```bash
ls masts/*.csv
ls mesos/*.txt
ls Justfile
just --list
```

- `masts/*.csv` — preprocessed mast data
- `mesos/*.txt` — ERA5 mesoscale data
- `Justfile` — the project Justfile (created by `cleanmast init`)

## Standard Workflow

```bash
just run-all
```

This runs all 16 Julia processing steps, then fill-heights,
wind turbine time series, and the report — in sequence.

## When Things Need Adjusting

`just run-all` chains every step in one command. If you need to
inspect, debug, or override a specific step, run them individually:

```bash
just recommend-parse-sensors
just parse-sensors
just recommend-clean
just process-clean
just recommend-tower-shading
just process-tower-shading
just recommend-reconstruct-single
just process-reconstruct-single
just recommend-train-cross
just process-train-cross
just recommend-reconstruct-cross
just process-reconstruct-cross
just recommend-train-meso
just process-train-meso
just recommend-reconstruct-meso
just process-reconstruct-meso
just recommend-representative-year
just process-representative-year
just recommend-fill-heights
just fill-heights-meso
just fill-heights-representative-year
just recommend-wt-timeseries
just process-wt-timeseries
just recommend-report-config
just report-timeseries
```

Common scenarios requiring overrides:

| Scenario | What To Do |
|----------|-----------|
| Masts have different recording periods | Override representative-year time ranges per-mast |
| Custom sensor configurations | Edit sensor format configs in `formats/` before parsing |
| Only want certain steps | Run individual `just <step>` commands instead of `run-all` |

## Override Pattern

When a `recommend-*` step generates a config that doesn't fit your
project, place an override script in `just-override/` and modify the
corresponding recipe in the Justfile to call it.

**Example**: Override representative-year time ranges.

See `@references/override-example/` for a real working example.

> **⚠️ WARNING**: The override files in `references/override-example/`
> are from a specific project (松原, 4 masts with uneven recording
> periods). They demonstrate the FORMAT of an override — do NOT copy
> the exact values or logic to another project unless you have
> verified they match that project's data profile. Every project has
> different masts, different date ranges, and different constraints.

## Key Justfile Recipes

| Recipe | What It Does |
|--------|-------------|
| `just run-all` | Full pipeline: parse → process → fill → report |
| `just --list` | Show all available recipes |
| `just process-<step>` | Run a single processing step |
| `just recommend-<step>` | Generate config for a single step |
| `just config` | Show resolved project/root paths |
