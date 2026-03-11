# Phase: On-Plan - Parquet Storage

## When to Use
Load this file during the planning/design phase when designing data persistence.

## Related ADR
- Main ADR: `adr/persistence-001-parquet-storage.md` (load first for constraints)

## Design Guidance

### Metadata Schema Design

```json
{
    "sensors": [
        {
            "name": "WS_80m",
            "height": 80,
            "orientation": "N",
            "sensor_type": "wind_speed",
            "column_index": 0
        }
    ],
    "time_column": "Timestamp",
    "frequency": "10min",
    "created_at": "2024-01-15T10:30:00Z"
}
```

### Key Considerations
- Sensor metadata must be serializable to JSON
- Column names in parquet should be human-readable
- Metadata should include version for future migrations
- Keep parquet schema simple - sensor info in metadata

### Repository Pattern
- Protocol defines interface (load/save)
- Implementation in infrastructure layer
- Domain layer depends on protocol only
- Multiple implementations possible (parquet, csv, etc.)

### Common Pitfalls
- Putting too much in parquet schema vs metadata
- Using separate metadata files
- Direct polars usage in domain layer
- Not versioning metadata schema

## Checklist
Before proceeding to implementation, verify:
- [ ] Metadata schema designed
- [ ] Repository protocol defined
- [ ] Sensor column mapping planned
- [ ] Versioning strategy for metadata
- [ ] ADR constraints are respected
