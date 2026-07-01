# Migration Status

**Last Updated**: 2026-07-01

## Overview

CleanMast uses both Julia and Python runtimes. Julia handles the core data processing pipeline (steps 1-16), while Python handles height filling (`fill-heights`), wind turbine time series (`wt-timeseries`), and report generation. The `mise run bootstrap` command installs all dependencies for both runtimes.

## Implementation Status

| Component | Julia | Python | Notes |
|-----------|-------|--------|-------|
| **Preprocessing** |
| Encoding Conversion | ✅ | ✅ | Python: `preprocess-tools` package |
| CSV Merging | ✅ | ✅ | Python: `preprocess-tools` package |
| Column Normalization | ✅ | ✅ | Python: `preprocess-tools` package |
| Timestamp Normalization | ✅ | ✅ | Python: `preprocess-tools` package |
| NRG Format Support | ✅ | ✅ | Python: `preprocess-tools` package |
| Lidar Format Support | ✅ | ✅ | Python: `preprocess-tools` package |
| **Core Processing** |
| Parse Sensors | ✅ | ⏳ | Julia only (via Justfile) |
| Data Cleaning | ✅ | ⏳ | Julia only (via Justfile) |
| Range Validation | ✅ | ⏳ | Julia only (via Justfile) |
| Layer Difference | ✅ | ⏳ | Julia only (via Justfile) |
| Icing Detection | ✅ | ⏳ | Julia only (via Justfile) |
| Tower Shading | ✅ | ⏳ | Julia only (via Justfile) |
| **Reconstruction** |
| Single Mast | ✅ | ⏳ | Julia only (via Justfile) |
| Mesoscale Integration | ✅ | ⏳ | Julia only (via Justfile) |
| Cross Mast | ✅ | ⏳ | Julia only (via Justfile) |
| Representative Year | ✅ | ⏳ | Julia only (via Justfile) |
| **Height Filling & Reports** |
| Fill Heights | ✅ | ✅ | Python: `cleanmast fill-heights` |
| WT Timeseries | ⏳ | ⏳ | Planned |
| Report Generation | ✅ | ✅ | Python: `cleanmast report` |
| Time Series Analysis | ✅ | ⏳ | Julia only |
| EN Standard Reports | ✅ | ⏳ | Julia only |
| Wind Rose Analysis | ✅ | ⏳ | Julia only |
| Quality Reports | ✅ | ⏳ | Julia only |

**Legend:**
- ✅ Complete and tested
- 🚧 In development
- ⏳ Planned
- ❌ Not planned

## Current Setup

**Setup**: `mise run bootstrap` (installs both Julia and Python dependencies)
**Interface**: Justfile recipes in project directory (`just --list` to see available commands)
**Project creation**: `mise run init:experiment projects/<name>`

## Workspace Structure

```
clean-mast-project/
├── mise.toml              # mise tasks (bootstrap)
├── Project.toml           # Julia workspace
├── pyproject.toml         # Python workspace
├── CleanMastProject/      # Julia implementation
├── packages/              # Python packages
│   ├── preprocess-tools/
│   └── cleanmast/
│       └── scaffold/      # Project template (Justfile)
└── projects/              # Project directories (each with Justfile)
```

## Next Steps

1. Complete sensor parsing module migration to Python
2. Migrate data cleaning rules to Python
3. Implement reconstruction algorithms in Python
4. Port analysis modules to Python

See [julia-to-python.md](julia-to-python.md) for migration guidelines.
