---
id: ddd-s-001-bounded-contexts
name: bounded-contexts
description: Explicit boundaries for CleanMast DDD contexts
tags: [ddd, bounded-context, cleanmast]
applies_when:
  - defining CleanMast boundaries
  - organizing contexts
  - refactoring existing code
---

# DDD-S-001: Bounded Contexts

## Constraint (MUST)

1. **Five contexts**: Configuration, PipelineContext, DataIngestion, DataProcessing, Assessment
2. **PascalCase names** - `DataIngestion`, `PipelineContext`
3. **Physical isolation**: Each context = separate package with own `subdomains/`
4. **NO direct imports**: Between contexts - use protocols/ACL
5. **SharedKernel**: Only `TimeSeriesData` as DTO, no business logic
Note: Assessment was formed by merging Analysis and Reporting due to tight coupling.

## Rationale (WHY)

CleanMast processes wind data through distinct phases (config → loading → cleaning → analysis → reporting). Each phase has different invariants. Explicit boundaries prevent "Sensor" from meaning different things in different contexts.

## Anti-Pattern (AVOID)

```python
# ❌ Direct context imports
from ..assessment.domain.services.calculators import WindRoseCalculator  # NEVER!

# ❌ Leaking domain models
class DataCleaner:
    def clean(self, ts: TimeSeriesData) -> TimeSeriesData:
        # Analysis-specific transforms here - NO!
        ...

# ❌ Vague boundaries
"Utils" or "Common" context  # NEVER
```

## Phase Links

| Phase | File |
|-------|------|
| Plan | [on-plan.md](./phases/ddd-s-001-bounded-contexts/on-plan.md) |
| Review Plan | [review-plan.md](./phases/ddd-s-001-bounded-contexts/review-plan.md) |
| Code | [code.md](./phases/ddd-s-001-bounded-contexts/code.md) |
| Review | [review-implementation.md](./phases/ddd-s-001-bounded-contexts/review-implementation.md) |

## References

- `ddd-s-002-context-maps.md` - Context relationships
- `structure-001-subdomain-layout.md` - Physical layout
