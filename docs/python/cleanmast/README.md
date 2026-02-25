# CleanMast Python Documentation

CleanMast Python implementation for wind energy data processing.

## Status

✅ **Report Generation**: Fully implemented
⏳ **Other modules**: In development

See [迁移状态](../../migration/status.md) for full migration progress.

## Available Modules

### Report Module ✅

Representative year timeseries report generation.

```bash
# Generate configuration from fill-heights data
uv run cleanmast recommend rep-ts-report projects/my-project

# Generate report (Typst + PDF + optional DOCX)
uv run cleanmast report rep-ts projects/my-project
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

- **Parse Sensors**: Data parsing and column mapping - Planning
- **Data Clean**: Validation rules and cleaning - Not started
- **Reconstruction**: Single/meso/cross reconstruction - Not started

## Julia Reference

For production use, see [Julia documentation](../../CleanMastProject/docs/).
