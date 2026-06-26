# ADR-DDD-S-003: wind_rose Subdomain Deepening

> Parent ADR: `assessment/adr-ddd-s-003-subdomain-deepening.md`
> References: `ddd-s-001-bounded-contexts.md`, `ddd-s-002-context-maps.md`, `structure-001-subdomain-layout.md`

## Role

Computes wind rose frequency distributions (16-sector polar) and renders charts + monthly grids.

## Concrete Structure

- `services/wind_rose_section.py` — WindRoseSection: unified calculate + build + render_ir()
- `entities/wind_rose_atom.py` — SingleMastWindRoseAtom (polar chart)
- `entities/wind_power_rose_atom.py` — SingleMastWindPowerRoseAtom (power density polar)
- `entities/monthly_wind_rose_grid_atom.py` — SingleMastMonthlyWindRoseGridAtom (3×4 grid)
- `value_objects/schemas.py` — WindRoseSchema, WindRoseMeta
- Depends on: `shared.protocols.Section`, `shared.protocols.ReportAtom`, `shared.protocols.DataSetAccess`
- Depends on: `shared.ir_types.*`, `shared.utils.subsection_renderer`
- No sub-subdomains (leaf node)

## Principles

1. **One service, one section, three atoms.**
   If this subdomain needs a second service class, it's probably two subdomains.

2. **Atoms are private implementation details.**
   No code outside this directory imports `SingleMastWindRoseAtom`. If the parent needs to
   reason about wind rose data, it goes through the Section protocol — not the atom type.

## Import Boundaries

- Imports: `shared.protocols`, `shared.ir_types`, `shared.utils`
- Imports: parent `adapters/` via `DataSetAccess` protocol (never direct import)
- Imports: own `entities/`, own `value_objects/`
- Forbidden: `weibull`, `turbulence`, or any other subdomain
- Forbidden: polars in entities layer (ok in services via DataSetAccess)
