---
id: ddd-s-002-context-maps
name: context-maps
description: Context relationships and integration patterns for CleanMast
tags: [ddd, context-map, integration, cleanmast]
applies_when:
  - integrating CleanMast contexts
  - defining context relationships
  - refactoring context boundaries
---

# DDD-S-002: Context Maps

## Constraint (MUST)

1. **Relationships documented** in context map
2. **Configuration → PipelineContext** (Customer-Supplier)
3. **PipelineContext coordinates all** - owns workflow orchestration
4. **DataIngestion → DataProcessing** (Customer-Supplier via Repository Protocol)
5. **DataProcessing → Analysis** (Customer-Supplier)
6. **Analysis → Reporting** (Conformist) - Reporting accepts Analysis output
7. **TimeSeriesRepository protocol** for data transfer

## Rationale (WHY)

Explicit relationships show dependencies. PipelineContext orchestrates. Repository protocol decouples DataIngestion from DataProcessing - ingestion doesn't know processing details.

## Anti-Pattern (AVOID)

```python
# ❌ Circular dependencies
DataProcessing importing Analysis  # NEVER

# ❌ Direct service calls
cleaner = DataCleaner()
analysis = WindRose(cleaner.clean(ts))  # Use repository

# ❌ Breaking protocol boundaries
class MyCleaner(DataCleaner):
    def _internal_parse(self):  # Accessing private
        ...
```

## Phase Links

| Phase | File |
|-------|------|
| Plan | [on-plan.md](./phases/ddd-s-002-context-maps/on-plan.md) |
| Review Plan | [review-plan.md](./phases/ddd-s-002-context-maps/review-plan.md) |
| Code | [code.md](./phases/ddd-s-002-context-maps/code.md) |
| Review | [review-implementation.md](./phases/ddd-s-002-context-maps/review-implementation.md) |

## References

- `ddd-s-001-bounded-contexts.md` - Context boundaries
- `persistence-001-parquet-storage.md` - Repository implementation
