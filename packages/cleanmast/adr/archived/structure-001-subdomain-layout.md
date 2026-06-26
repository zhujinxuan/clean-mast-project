---
id: structure-001-subdomain-layout
name: subdomain-layout
description: CleanMast DDD folder structure with subdomain organization
tags: [structure, layout, ddd, cleanmast]
applies_when:
  - organizing CleanMast code
  - creating new contexts
  - refactoring structure
status: proposed
enforced: true
---

<!-- ADR-GUARDRAILS: ddd-s-001-bounded-contexts, ddd-s-003-subdomain-deepening -->

# STRUCTURE-001: Subdomain Layout

## Constraint (MUST)
1. **Contexts in `src/subdomains/`** - assessment, configuration, dataingestion, dataprocessing, pipeline
2. **Each context has DDD folders** - organize by capability
3. **Domain layer** has NO external dependencies (no polars, pandas, I/O)
4. **Application layer** (`application/`) orchestrates use cases
5. **Infrastructure layer** (`infrastructure/`) has I/O
6. **Protocols in `domain/protocols/`** - define interfaces (for layered pattern)

## Folder Structure

```
src/subdomains/
├── {context}/              # One of: assessment, configuration, dataingestion, dataprocessing, pipeline
│   ├── domain/             # Domain layer (layered pattern only)
│   │   ├── entities/
│   │   ├── protocols/
│   │   ├── services/
│   │   └── value_objects/
│   ├── application/        # Application layer (layered pattern only)
│   │   └── services/
│   ├── infrastructure/     # Infrastructure layer
│   ├── entities/           # Flat pattern: domain entities
│   ├── value_objects/      # Flat pattern: value objects
│   ├── services/           # Flat pattern: domain services
│   └── ...                 # Other DDD folders as needed
```

## Current Patterns

### Layered Pattern (assessment)
Full 3-layer architecture with nested domain/application/infrastructure:
```
assessment/
├── domain/entities/, domain/protocols/, domain/services/, domain/value_objects/
├── application/services/
└── infrastructure/
```

### Organized-Flat Pattern (dataingestion)
DDD folders without layer nesting:
```
dataingestion/
├── entities/, value_objects/, repositories/, services/, infrastructure/
```

### Minimal-Flat Pattern (configuration, dataprocessing, pipeline)
Essential folders only, domain logic in flat structure:
```
configuration/     dataprocessing/        pipeline/
├── services/      ├── commands/          ├── entities/
└── value_objects/ ├── services/          └── services/
                   └── strategies/
```

### Nested Subdomain Pattern (Matryoshka)
Domains that contain sub-domains as capability modules. Each sub-domain is physically isolated with its own entities/, services/, value_objects/, and adr-{adr-id}.md. Subdomains import only from shared/ and parent adapters/ via protocols.

```
{context}/
├── shared/                    ← protocols + value_objects + ir_types + utils
├── adapters/                  ← concrete adapter implementations
├── domain/services/           ← orchestrator (calls subdomains)
├── subdomains/
│   ├── {subdomain_a}/
│   │   ├── adr-{adr-id}.md    ← per-domain ADR
│   │   ├── entities/          ← private atoms
│   │   ├── services/          ← unified SectionService
│   │   └── value_objects/     ← private schemas
│   └── {subdomain_b}/
└── ...
```

Target-state pattern (proposed). Currently only planned for assessment domain. See ddd-s-003-subdomain-deepening.md.

## Pattern Promotion

**When to graduate patterns:**
- Minimal-flat → Organized-flat: Add repositories, more entities
- Organized-flat → Layered: Need clear separation, multiple application services, protocols
- Organized-flat with >5 capability groups → Nested subdomain: Split into subdomains with shared/ kernel

## Principles

1. **Simplicity by default, complexity when warranted.**
   The minimal-flat pattern is the default. Graduate to nested subdomain only when
   a domain has >5 independent capability groups. Don't over-engineer early.

2. **Physical layout mirrors conceptual boundaries.**
   Directory structure IS the architecture diagram. If two concepts are separated
   in the domain language, their files should live in different directories.

3. **Pattern promotion is one-way.**
   Minimal-flat → Organized-flat → Layered → Nested subdomain. Never go backward
   without explicit justification. Each promotion adds structure that must be maintained.

## Note on Aggregates

In DDD, **Aggregate Roots ARE Entities**. They belong in the `entities/` folder, not a separate `aggregates/` folder.

## Rationale (WHY)

- **Layered architecture**: Clear separation where needed
- **Flat patterns**: Pragmatic for simpler subdomains
- **Dependency inversion**: Protocols allow abstraction dependencies
- **Testability**: Domain layer has no I/O dependencies

## Anti-Pattern (AVOID)
```python
# ❌ Flat files at src/ root (no context)
src/parse.py, src/clean.py

# ❌ Infrastructure in domain layer
subdomains/a/domain/db.py  # NEVER - use infrastructure/

# ❌ Cross-context imports
subdomains/a/... imports subdomains/b/...  # NEVER
```

Note: "Flat" folder structure WITHIN a context (e.g., `entities/` at context root) is acceptable and distinct from flat files at project root.

## Phase Links
| Phase | File |
|-------|------|
| Plan | [on-plan.md](./phases/structure-001-subdomain-layout/on-plan.md) |
| Review Plan | [review-plan.md](./phases/structure-001-subdomain-layout/review-plan.md) |
| Code | [code.md](./phases/structure-001-subdomain-layout/code.md) |
| Review | [review-implementation.md](./phases/structure-001-subdomain-layout/review-implementation.md) |

## Enforcement

- **method**: agentic-lint
- **description**: Subagent validates directory structure matches one of 4 allowed patterns, shared/ contains only protocols/utils, and per-domain ADRs exist where required
- **triggers**: new directories under `subdomains/`, changes to `__init__.py` structure

## References
- `ddd-s-001-bounded-contexts.md` - Context boundaries
- `ddd-s-003-subdomain-deepening.md` - Nested subdomain pattern
