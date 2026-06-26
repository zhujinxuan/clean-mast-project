---
id: persistence-001-parquet-storage
name: parquet-storage
description: Parquet persistence with embedded sensor metadata
tags: [persistence, parquet, sensor, cleanmast]
applies_when:
  - saving TimeSeriesData
  - loading sensor data
  - implementing repositories
---

# PERSISTENCE-001: Parquet Storage

## Constraint (MUST)
1. **Parquet files** store time series data (columnar format)
2. **Sensor metadata embedded** in parquet custom metadata (JSON)
3. **TimeSeriesRepository protocol** for all persistence operations
4. **Separate metadata from data** - parquet for data, metadata for schema
5. **File-based Julia integration** - Parquet + ACL (not memory)
6. **SensorColumn metadata**: columnName, sensorType, sensorDirection, height, statType, unit

## Rationale (WHY)

Parquet provides fast columnar storage. Embedding metadata keeps data + schema together. Protocol decouples persistence from domain. File-based Julia integration is language-agnostic.

## Anti-Pattern (AVOID)

```python
# ❌ Direct polars in domain
class DataCleaner:
    def clean(self, df: pl.DataFrame):  # NEVER - use TimeSeriesData
        ...
# ❌ Metadata in separate file
path.with_suffix(".meta.json")  # NEVER - embed in parquet
jl.eval("process_data")(df.to_numpy())  # NEVER - use files
```

## Phase Links
| Phase | File |
|-------|------|
| Plan | [on-plan.md](./phases/persistence-001-parquet-storage/on-plan.md) |
| Review Plan | [review-plan.md](./phases/persistence-001-parquet-storage/review-plan.md) |
| Code | [code.md](./phases/persistence-001-parquet-storage/code.md) |
| Review | [review-implementation.md](./phases/persistence-001-parquet-storage/review-implementation.md) |
## References
- `ddd-s-002-context-maps.md` - Repository protocol usage
- `pipeline-001-orchestration.md` - Julia integration via files
