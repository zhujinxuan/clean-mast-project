# Design Rationale: DDD Architecture Deepening

> **Permanent reference for Sisyphus execution.**
> Contains the COMPLETE L1/L2/L3 ADR content with all Principles text.
> Plan tasks 3, 6, 8, 9 must use this as their authoritative source.

---

## L1: Architecture ADR (`ddd-s-003-subdomain-deepening.md`)

### Concrete Structure (7 bullets)

- **shared/**: protocols (Section, ReportAtom, DataSetAccess) + adapter_protocols (ConfigProvider, DataLoader) + ir_types (TypstHeading, TypstSection, TypstBody) + utils (subsection_renderer, merge)
- **adapters/**: concrete DataSetAccess, ConfigProvider, DataLoader implementations
- **parent domain**: ReportAssemblyService orchestrates, owns AtomCollection
- **subdomains**: one per capability group (wind_rose, weibull, ...), each with entities/ + services/ + value_objects/
- **per-domain ADR**: `adr-{adr-id}.md` in each domain/subdomain — if >40 lines, split the domain
- **import rule**: subdomain → shared/ + parent adapters/ (via protocols) + self only. No cross-subdomain imports
- **service pattern**: one unified SectionService per subdomain (calculates + builds + renders)

### Principles (3)

1. **Physical isolation = enforced discipline.**
   If two capabilities share a directory, they will cross-import. Directories ARE boundaries.

2. **ADR length as self-diagnosis.**
   A per-domain ADR that runs long is the codebase telling you it's too compressed.
   Don't add more rules — split the domain.

3. **Protocols gate all external access.**
   A subdomain never imports another subdomain's concrete type. If it needs data,
   it goes through a protocol in shared/. The protocol is the API.

### Import Rule Matrix

| From | To shared/ | To parent adapters/ | To own entities/ | To other subdomains |
|------|-----------|--------------------|--------------------|--------------------|
| subdomain | ✅ (protocols) | ✅ (via protocols) | ✅ | ❌ |
| parent domain | ✅ | ✅ | ✅ | ✅ (orchestrates all) |

### Per-Domain ADR Required Sections

- **Role**: 1 sentence
- **Concrete Structure**: services, entities, imports, dependencies (bullet list)
- **Principles**: 2-4 distilled insights, fewer than concrete bullets

> **Self-diagnostic rule**: If Principles has more items than Concrete Structure, you haven't abstracted enough. If the whole file exceeds ~40 lines, the domain is too compressed — split it.

---

## L2: Parent Domain ADR (`assessment/adr-ddd-s-003-subdomain-deepening.md`)

### Role

Orchestrates report assembly: calls 10 subdomain services and builds the unified TypstSection tree.

### Concrete Structure (9 bullets)

- `shared/protocols/` — Section, ReportAtom, DataSetAccess (ABCs all subdomains depend on)
- `shared/adapter_protocols/` — ConfigProvider, DataLoader
- `shared/ir_types/` — TypstHeading, TypstSection, TypstBody
- `shared/utils/` — subsection_renderer, merge, height_filter (pure, stateless)
- `adapters/` — ParquetDataSet, TomlConfig, TimeSeriesLoader (concrete, implements shared protocols)
- `domain/services/report_assembly.py` — ReportAssemblyService (sole orchestrator)
- `domain/entities/atom_collection.py` — AtomCollection (shared data structure)
- `subdomains/` — 10 capability subdomains, each with `adr-{adr-id}.md`
- Subdomains called: wind_rose, weibull, turbulence, wind_frequency, wind_temporal, vertical_profile,
  extreme_wind, representative_year, air_density, iec_standards

### Principles (3)

1. **The parent doesn't compute — it composes.**
   ReportAssemblyService owns no domain logic. It calls subdomains and wires their outputs.
   If it starts calculating, something belongs in a subdomain.

2. **shared/ is a contract surface, not a dumping ground.**
   Every item in shared/ is used by ≥2 subdomains. If only one subdomain uses it,
   it belongs in that subdomain. Adapter protocols in shared/ enable dependency inversion
   — subdomains never import concrete adapter implementations.

3. **Ten subdomains, ten ADR files, ten self-diagnoses.**
   Each subdomain's `adr-{adr-id}.md` is a mirror. If one is long and the others short,
   that subdomain is doing too much. Split it before adding more services.

### Import Boundaries

- ✅ Imports from: `shared/`, `adapters/`, own `domain/`
- ✅ Imports from: all subdomains (orchestrator role — the sole exception to cross-subdomain rule)
- ❌ Forbidden: polars/pandas in domain layer

---

## L3: wind_rose Subdomain ADR (`wind_rose/adr-ddd-s-003-subdomain-deepening.md`)

### Role

Computes wind rose frequency distributions (16-sector polar) and renders charts + monthly grids.

### Concrete Structure (7 bullets)

- `services/wind_rose_section.py` — WindRoseSection: unified calculate + build + render_ir()
- `entities/wind_rose_atom.py` — SingleMastWindRoseAtom (polar chart)
- `entities/wind_power_rose_atom.py` — SingleMastWindPowerRoseAtom (power density polar)
- `entities/monthly_wind_rose_grid_atom.py` — SingleMastMonthlyWindRoseGridAtom (3×4 grid)
- `value_objects/schemas.py` — WindRoseSchema, WindRoseMeta
- Depends on: `shared.protocols.Section`, `shared.protocols.ReportAtom`, `shared.protocols.DataSetAccess`
- Depends on: `shared.ir_types.*`, `shared.utils.subsection_renderer`
- No sub-subdomains (leaf node)

### Principles (2)

1. **One service, one section, three atoms.**
   If this subdomain needs a second service class, it's probably two subdomains.

2. **Atoms are private implementation details.**
   No code outside this directory imports `SingleMastWindRoseAtom`. If the parent needs to
   reason about wind rose data, it goes through the Section protocol — not the atom type.

### Import Boundaries

- ✅ Imports: `shared.protocols`, `shared.ir_types`, `shared.utils`
- ✅ Imports: parent `adapters/` via `DataSetAccess` protocol (never direct import)
- ✅ Imports: own `entities/`, own `value_objects/`
- ❌ Forbidden: `weibull`, `turbulence`, or any other subdomain
- ❌ Forbidden: polars in entities layer (ok in services via DataSetAccess)

---

## L3: extreme_wind Subdomain ADR (`extreme_wind/adr-ddd-s-003-subdomain-deepening.md`)

### Role

Computes 50-year extreme wind speed estimates using 3 statistical methods + summary,
renders as report section with 4 internal subsections.

### Concrete Structure

- `services/extreme_wind_section.py` — ExtremeWindSection (parent, wires 4 subsections)
- `services/method1_section.py` — Method1Subsection (Gumbel)
- `services/method2_section.py` — Method2Subsection
- `services/method3_section.py` — Method3Subsection
- `services/summary_section.py` — SummarySubsection
- `entities/` — 4 atoms: method1, method2, method3, summary
- `value_objects/schemas.py` — Method schemas, ExtremeWindMeta
- Depends on: `shared.protocols.Section`, `shared.protocols.DataSetAccess`, `shared.ir_types.*`, `shared.utils.subsection_renderer`

### Principles (2)

1. **One parent section, four child subsections.**
   Internal nesting mirrors the report structure itself — the subdomain is the extreme wind
   chapter, not each method. If method1 needs its own subdomain, the diagnostic is that
   extreme_wind is too compressed.

2. **Methods are siblings, not sub-subdomains.**
   Currently 4 methods × 1 service each = appropriate granularity. If any method grows its
   own subtree of subsections, promote it to a separate subdomain.

---

## 10 Subdomains Table

| Subdomain | Atoms | Service Name | Current Path | Notes |
|-----------|-------|-------------|-------------|-------|
| wind_rose | 3 | WindRoseSection | entities/single_mast/wind_rose.py | Leaf |
| weibull | 4 | WeibullSection | entities/single_mast/weibull_subgrid.py | Leaf |
| turbulence | 5 | TurbulenceSection | entities/single_mast/turbulence_*.py | Leaf |
| wind_frequency | 4 | WindFrequencySection | entities/single_mast/wind_frequency_hours.py | Leaf |
| wind_temporal | 7 | WindTemporalSection | entities/single_mast/daily_pattern.py | Leaf |
| vertical_profile | 3 | VerticalProfileSection | entities/single_mast/wind_shear_matrix.py | Leaf |
| extreme_wind | 4 | ExtremeWindSection | services/sections/fifty_year_max_wind_section.py | Has 4 internal subsections |
| representative_year | 1 | RepresentativeYearSection | entities/multi_masts/representative_year_calibration.py | Leaf |
| air_density | 1 | AirDensitySection | entities/multi_masts/air_density.py | Leaf |
| iec_standards | 1 | IECStandardsSection | entities/no_masts/iec_standards.py | Leaf |

---

## Design Decisions Log

| Decision | Rationale |
|----------|-----------|
| 10 subdomains | Each report subsection is an independent analysis capability |
| Parent orchestrates, children render | ReportAssemblyService is the sole wiring point |
| shared/ = protocols only | Dependency inversion; no concrete code in shared kernel |
| adapters/ = concrete implementations | DataSetAccess, ConfigProvider, DataLoader live here |
| One service per subdomain | Calculator + builder + section merged into unified SectionService |
| Private entities | Subdomain atoms are NOT exposed externally — access via Section protocol |
| No cross-subdomain imports | Physical isolation = enforced discipline |
| Per-domain ADR format: Role → Concrete Structure → Principles | Principles must be fewer and more abstract than bullets |
| Self-diagnostic: >40 lines = too compressed | ADR length as architectural health signal |
| All ADRs status = "proposed" | Target-state documentation, not current reality |

(End of file - total 190 lines)
