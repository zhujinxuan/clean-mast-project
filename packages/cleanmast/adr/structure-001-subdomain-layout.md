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
1. **Contexts in `src/subdomains/`** - dataingestion, dataprocessing, etc.
2. **Each context has `subdomains/`** - organize by capability
3. **Domain layer** (`subdomains/`) has NO external dependencies
4. **Application layer** (`application/`) orchestrates use cases
5. **Infrastructure layer** (`infrastructure/`) has I/O
6. **Protocols in `domain/protocols/`** - define interfaces

## Folder Structure

```
src/subdomains/
├── subdomains/           # Domain layer - pure business logic
│   └── {subdomain}/
│       ├── entities/
│       ├── value_objects/
│       └── domain_services/
├── application/          # Application layer - use cases
└── infrastructure/       # Infrastructure layer - I/O
```

## Note on Aggregates

In DDD, **Aggregate Roots ARE Entities**. They belong in the `entities/` folder, not a separate `aggregates/` folder. The `entities/` folder may contain:
- **Simple Entities**: Business objects with identity (e.g., `Sensor`)
- **Aggregate Roots**: Entities that define consistency boundaries (e.g., `TimeSeries`)

This follows DDD semantics where an Aggregate Root is just a special type of Entity that protects invariants across a cluster of objects.

## Rationale (WHY)

- **Layered architecture**: Clear separation of concerns
- **Dependency inversion**: Protocols allow abstraction dependencies
- **Testability**: Domain layer has no I/O dependencies

## Anti-Pattern (AVOID)
```python
# ❌ Flat structure
src/parse.py, src/clean.py  # NEVER - organize by context/subdomain
# ❌ Infrastructure in domain
subdomains/parsing/db.py  # NEVER - use infrastructure/
subdomains/a/... imports subdomains/b/...  # NEVER
```

## Phase Links
| Phase | File |
|-------|------|
| Plan | [on-plan.md](./phases/structure-001-subdomain-layout/on-plan.md) |
| Review Plan | [review-plan.md](./phases/structure-001-subdomain-layout/review-plan.md) |
| Code | [code.md](./phases/structure-001-subdomain-layout/code.md) |
| Review | [review-implementation.md](./phases/structure-001-subdomain-layout/review-implementation.md) |
## References
- `ddd-s-001-bounded-contexts.md` - Context boundaries
