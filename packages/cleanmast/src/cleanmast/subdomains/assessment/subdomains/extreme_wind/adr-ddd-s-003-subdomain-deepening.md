# ADR-DDD-S-003: Subdomain Deepening — extreme_wind

> Parent ADR: [assessment/adr-ddd-s-003-subdomain-deepening.md](../adr-ddd-s-003-subdomain-deepening.md)
> References: `ddd-s-001-bounded-contexts.md`, `ddd-s-002-context-maps.md`, `structure-001-subdomain-layout.md`

## Role

Computes 50-year extreme wind speed estimates using 3 statistical methods + summary,
renders as report section with 4 internal subsections.

## Concrete Structure

- `services/extreme_wind_section.py` — ExtremeWindSection (parent, wires 4 subsections)
- `services/method1_section.py` — Method1Subsection (Gumbel)
- `services/method2_section.py` — Method2Subsection
- `services/method3_section.py` — Method3Subsection
- `services/summary_section.py` — SummarySubsection
- `entities/` — 4 atoms: method1, method2, method3, summary
- `value_objects/schemas.py` — Method schemas, ExtremeWindMeta
- Depends on: `shared.protocols.Section`, `shared.protocols.DataSetAccess`, `shared.ir_types.*`, `shared.utils.subsection_renderer`

## Principles

1. **One parent section, four child subsections.**
   Internal nesting mirrors the report structure itself — the subdomain is the extreme wind
   chapter, not each method. If method1 needs its own subdomain, the diagnostic is that
   extreme_wind is too compressed.

2. **Methods are siblings, not sub-subdomains.**
   Currently 4 methods × 1 service each = appropriate granularity. If any method grows its
   own subtree of subsections, promote it to a separate subdomain.

## Import Boundaries

- Imports: `shared.protocols`, `shared.ir_types`, `shared.utils`
- Imports: parent `adapters/` via `DataSetAccess` protocol (never direct import)
- Imports: own `entities/`, own `value_objects/`
- Forbidden: `wind_rose`, `weibull`, `turbulence`, or any other subdomain
- Forbidden: polars in entities layer (ok in services via DataSetAccess)
