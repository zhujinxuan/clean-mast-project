---
id: structure-001-subdomain-layout
name: subdomain-layout
description: CleanMast DDD folder structure with subdomain organization
tags: [structure, layout, ddd, cleanmast]
applies_when:
  - organizing CleanMast code
  - creating new contexts
  - refactoring structure
---

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

## Pattern Promotion

**When to graduate patterns:**
- Minimal-flat → Organized-flat: Add repositories, more entities
- Organized-flat → Layered: Need clear separation, multiple application services, protocols

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

## References
- `ddd-s-001-bounded-contexts.md` - Context boundaries
