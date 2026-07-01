# CleanMast Python Documentation

CleanMast Python implementation for wind energy data processing.

## Status

✅ **Report Generation**: Fully implemented
✅ **Fill Heights**: Fully implemented
⏳ **WT Timeseries**: In development
⏳ **Other modules**: In development

See [Migration Status](../../migration/status.md) for full progress.

## Available Modules

### Fill Heights Module ✅

Wind speed and direction height extrapolation and interpolation.

```bash
# Generate configuration
uv run cleanmast recommend fill-heights projects/my-project -h 120,140,160

# Execute height filling
uv run cleanmast fill-heights projects/my-project/fill-heights-reconstruct-meso.toml
```

### Report Module ✅

Representative year timeseries report generation.

```bash
# Generate configuration
uv run cleanmast recommend report-configs timeseries projects/my-project

# Generate report (Typst + PDF + optional DOCX)
uv run cleanmast report timeseries projects/my-project/rep-ts-report.toml
```

**Output:**
- `rep-ts/report.typ` - Typst source
- `rep-ts/report.pdf` - Compiled PDF
- `rep-ts/report.docx` - Word document (if typ2docx installed)
- `rep-ts/images/*.png` - Charts

**Features:**
- 4 report atom types (wind, power, frequency rose, power rose)
- Altair visualization
- Content-addressable caching
- Chinese text throughout

See [Architecture](../../CleanMastProject/docs/c4/03-component/reporting.md) for design details.

## Architecture

```
cleanmast/
├── report/              # ✅ Report generation (COMPLETE)
│   ├── atom.py         # ReportAtom base class
│   ├── builder.py      # Report orchestration
│   ├── compiler.py     # PDF/DOCX compilation
│   ├── renderer.py     # Typst helpers
│   ├── meta.py         # SingleMastMeta + helpers
│   └── atoms/          # Report atom implementations
│       └── single_mast/
│           ├── monthly_wind.py
│           ├── monthly_wind_power.py
│           ├── wind_rose.py
│           └── schemas.py
├── fill_heights/       # ✅ Height filling (COMPLETE)
├── wt_timeseries/      # ⏳ Wind turbine time series (WIP)
└── io/                 # ⏳ Data I/O (WIP)
```

## In Development

- **WT Timeseries**: Wind turbine time series generation
- **Parse Sensors**: Data parsing and column mapping
- **Data Clean**: Validation rules and cleaning
- **Reconstruction**: Single/meso/cross reconstruction

## Julia Reference

The Julia implementation in [CleanMastProject/](../../CleanMastProject/) handles the core data processing pipeline (steps 1-16). Python modules handle fill-heights, wt-timeseries, and report generation.
