---
id: ddd-s-003-subdomain-deepening
name: subdomain-deepening
description: Nested subdomain pattern for decomposing monolithic domains into isolated capability modules
tags: [ddd, subdomain, structure, nested, strategic]
applies_when:
  - a domain has >5 independent capability groups
  - sections/entities are flat and cross-import freely
  - a single domain's ADR is too long to stay concise
status: proposed
enforced: true
---

# DDD-S-003: Subdomain Deepening

## Constraint (MUST)

- shared/ = protocols + value_objects + adapter_protocols (ConfigProvider, DataLoader) + ir_types (TypstHeading, TypstSection, TypstBody) + utils (subsection_renderer, merge)
- adapters/ = concrete implementations of shared adapter_protocols (NOT in this phase — directory scaffolding only with docstring)
- Parent domain orchestrates via ReportAssemblyService; owns AtomCollection
- Subdomains: one per capability group, each with entities/ + services/ + value_objects/ + adr-{adr-id}.md
- Per-domain ADR: if >~40 lines, split the domain
- Import rule: subdomain → shared/ + parent adapters/ (via protocols) + self only. NO cross-subdomain
- Service pattern: one unified SectionService per subdomain

## Principles

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

## Rationale (WHY)

Flat domains with 26+ entities and 15+ sections in one directory create uncontrolled cross-imports. Nested subdomains provide physical isolation, clear import rules, and self-diagnosis via per-domain ADR length.

## Anti-Pattern (AVOID)

```python
# ❌ Cross-subdomain import
from ..weibull.entities.weibull_atom import WeibullAtom  # NEVER

# ❌ Concrete adapter import in subdomain
from ...adapters.parquet_dataset import ParquetDataSet  # NEVER - use protocol

# ✅ Correct: via protocols
from assessment.shared.protocols import Section, DataSetAccess
```

## Phase Links

| Phase | File |
|-------|------|
| Plan | [on-plan.md](./phases/ddd-s-003-subdomain-deepening/on-plan.md) |
| Code | [code.md](./phases/ddd-s-003-subdomain-deepening/code.md) |
| Review Plan | [review-plan.md](./phases/ddd-s-003-subdomain-deepening/review-plan.md) |
| Review Impl | [review-implementation.md](./phases/ddd-s-003-subdomain-deepening/review-implementation.md) |

## Enforcement

- **method**: agentic-lint
- **description**: Subagent validates nested subdomain structure, import isolation, shared/ purity, and per-domain ADR compliance per `review-implementation.md`
- **triggers**: code changes under `subdomains/assessment/subdomains/`, `subdomains/assessment/shared/`, `subdomains/assessment/adapters/`

## References

- `ddd-s-001-bounded-contexts.md` - Context boundaries
- `ddd-s-002-context-maps.md` - Context relationships
- `structure-001-subdomain-layout.md` - Physical layout patterns
