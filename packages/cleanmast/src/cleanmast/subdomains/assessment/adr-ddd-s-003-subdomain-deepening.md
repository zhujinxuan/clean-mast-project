> Following `packages/cleanmast/adr/ddd-s-003-subdomain-deepening.md`
> References: `ddd-s-001-bounded-contexts.md`, `ddd-s-002-context-maps.md`, `structure-001-subdomain-layout.md`

## Role

Orchestrates report assembly: calls 10 subdomain services and builds the unified TypstSection tree.

## Concrete Structure

- `shared/protocols/` — Section, ReportAtom, DataSetAccess (ABCs all subdomains depend on)
- `shared/adapter_protocols/` — ConfigProvider, DataLoader
- `shared/ir_types/` — TypstHeading, TypstSection, TypstBody
- `shared/utils/` — subsection_renderer, merge, height_filter (pure, stateless)
- `adapters/` — ParquetDataSet, TomlConfig, TimeSeriesLoader (concrete, implements shared protocols)
- `domain/services/report_assembly.py` — ReportAssemblyService (sole orchestrator)
- `domain/entities/atom_collection.py` — AtomCollection (shared data structure)
- `subdomains/` — 10 capability subdomains, each with `adr-{adr-id}.md`
- Subdomains called: wind_rose, weibull, turbulence, wind_frequency, wind_temporal, vertical_profile, extreme_wind, representative_year, air_density

## Principles

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
