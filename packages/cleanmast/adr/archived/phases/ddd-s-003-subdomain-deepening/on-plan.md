# Phase: On-Plan - Subdomain Deepening

## When to Use

Load this file during the planning/design phase when a domain has grown too large and needs to be split into nested subdomains.

## Related ADR

- Main ADR: `adr/ddd-s-003-subdomain-deepening.md` (load first for constraints)

## Design Guidance

### When to Create Nested Subdomains

Split a domain into nested subdomains when ANY of these conditions are true:

1. **More than 5 independent capability groups.** A domain with 6+ unrelated features (wind rose, Weibull, turbulence, etc.) has too many concerns in one directory.
2. **Sections/entities are flat and cross-import freely.** If `weibull.py` imports `from ..wind_rose import WindRoseAtom`, physical isolation has already failed.
3. **A single domain's ADR exceeds ~40 lines.** ADR length is a self-diagnostic. Long ADRs signal too much complexity compressed into one unit.

### How to Design `shared/`

The `shared/` directory is a **contract surface**, not a dumping ground. It contains exactly four categories:

```
shared/
├── protocols/           # ABCs all subdomains depend on
│   ├── section.py       # Section protocol (render_ir)
│   ├── report_atom.py   # ReportAtom protocol
│   └── dataset_access.py # DataSetAccess protocol
├── adapter_protocols/   # Protocols for external concerns
│   ├── config_provider.py
│   └── data_loader.py
├── ir_types/            # Typst IR node types
│   ├── heading.py
│   ├── section.py
│   └── body.py
└── utils/               # Pure, stateless helpers
    ├── subsection_renderer.py
    └── merge.py
```

Rules for `shared/`:
- Every item is used by **2+ subdomains**. If only one subdomain uses it, it belongs in that subdomain.
- NO concrete implementations. Only protocols, IR types, and pure functions.
- NO domain logic. shared/ is plumbing, not business rules.

### How to Design `adapters/`

The `adapters/` directory contains **concrete implementations** of protocols defined in `shared/adapter_protocols/`:

```
adapters/
├── __init__.py
├── parquet_dataset.py    # Implements DataSetAccess
├── toml_config.py        # Implements ConfigProvider
└── time_series_loader.py # Implements DataLoader
```

Rules for `adapters/`:
- Each file implements **one** shared protocol.
- Subdomains import protocols, not adapters. `from shared.protocols import DataSetAccess` — NOT `from adapters.parquet_dataset import ParquetDataSet`.
- Adapters are I/O-heavy (polars, file reads, network). They live at the parent level because multiple subdomains may share the same data source.

### How to Split into Subdomains

One subdomain per **capability group**. A capability group is a coherent set of business rules that produce one report section:

```
subdomains/
├── wind_rose/           # One capability: polar charts + monthly grids
├── weibull/             # One capability: distribution fitting
├── turbulence/          # One capability: TI analysis
├── wind_frequency/      # One capability: frequency tables
├── wind_temporal/       # One capability: daily/monthly patterns
├── vertical_profile/    # One capability: shear + profile
├── extreme_wind/        # One capability: 50-year estimates
├── air_density/         # One capability: density calculations
├── representative_year/ # One capability: rep year calibration
└── iec_standards/       # One capability: standards compliance
```

Each subdomain follows this structure:

```
wind_rose/
├── entities/            # Atoms (private implementation details)
├── services/            # One SectionService (unified calculate + build + render_ir)
├── value_objects/       # Schemas, metadata
└── adr-ddd-s-003.md     # Per-domain ADR
```

### Per-Domain ADR Template

Every subdomain MUST have an `adr-{adr-id}.md` file with exactly three sections:

**Role** — 1 sentence describing what this subdomain computes or renders.

```markdown
## Role

Computes wind rose frequency distributions (16-sector polar) and renders charts + monthly grids.
```

**Concrete Structure** — Bullet list of services, entities, value objects, and dependencies.

```markdown
## Concrete Structure

- `services/wind_rose_section.py` — WindRoseSection: unified calculate + build + render_ir()
- `entities/wind_rose_atom.py` — SingleMastWindRoseAtom (polar chart)
- `value_objects/schemas.py` — WindRoseSchema, WindRoseMeta
- Depends on: `shared.protocols.Section`, `shared.protocols.DataSetAccess`
- No sub-subdomains (leaf node)
```

**Principles** — 2-4 distilled insights. Fewer bullets than concrete structure items.

```markdown
## Principles

1. **One service, one section, three atoms.**
   If this subdomain needs a second service class, it's probably two subdomains.

2. **Atoms are private implementation details.**
   No code outside this directory imports `SingleMastWindRoseAtom`.
```

### Self-Diagnostic: ADR Length

If a per-domain ADR exceeds **~40 lines**, the subdomain is too compressed. Do not add more rules. Split it:

1. Identify the service or entity group that could stand alone.
2. Create a new subdomain for that group.
3. Move the files and update the parent ADR.

**Example diagnostic:**
- `extreme_wind` ADR at 39 lines — OK.
- `extreme_wind` ADR at 55 lines with 6 subsections and 8 atoms — split into `extreme_wind_method1`, `extreme_wind_method2`, etc.

## Checklist

Before proceeding to implementation, verify:
- [ ] Domain has >5 independent capability groups OR cross-imports OR long ADR
- [ ] `shared/` contains only protocols + IR types + utils (no concrete code)
- [ ] `adapters/` contains only concrete implementations of shared protocols
- [ ] One subdomain per capability group
- [ ] Each subdomain has `entities/`, `services/`, `value_objects/`, and `adr-{adr-id}.md`
- [ ] Per-domain ADR follows Role → Concrete Structure → Principles format
- [ ] No per-domain ADR exceeds ~40 lines
- [ ] ADR constraints are respected
