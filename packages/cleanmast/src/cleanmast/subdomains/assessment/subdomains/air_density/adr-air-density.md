# ADR-DDD-S-003: air_density Subdomain Deepening

> Parent ADR: `assessment/adr-ddd-s-003-subdomain-deepening.md`
> References: `ddd-s-001-bounded-contexts.md`, `ddd-s-002-context-maps.md`, `structure-001-subdomain-layout.md`

## Role

Computes multi-mast air density with height-adjusted values.

## Concrete Structure

- `services/air_density_section.py` — AirDensitySection: unified calculate + build + render_ir()
- `entities/air_density_atom.py` — MultiMastAirDensityAtom (height-adjusted density table)
- `value_objects/schemas.py` — MultiMastAirDensitySchema, AirDensityMeta
- Depends on: `shared.protocols.Section`, `shared.protocols.ReportAtom`, `shared.protocols.DataSetAccess`
- Depends on: `shared.ir_types.*`, `shared.utils.subsection_renderer`
- No sub-subdomains (leaf node)

## Principles

1. **One service, one section, one atom.**
   If this subdomain needs a second service class, it's probably two subdomains.

2. **Atoms are private implementation details.**
   No code outside this directory imports `MultiMastAirDensityAtom`. If the parent needs to
   reason about air density data, it goes through the Section protocol — not the atom type.

## Import Boundaries

- Imports: `shared.protocols`, `shared.ir_types`, `shared.utils`
- Imports: parent `adapters/` via `DataSetAccess` protocol (never direct import)
- Imports: own `entities/`, own `value_objects/`
- Forbidden: `weibull`, `turbulence`, or any other subdomain
- Forbidden: polars in entities layer (ok in services via DataSetAccess)
