# Phase: Review-Plan - Parquet Storage

## When to Use
Load this file when reviewing a design/plan for data persistence.

## Related ADR
- Main ADR: `adr/persistence-001-parquet-storage.md` (verify compliance)

## Review Guidance

### Key Review Points
1. **Parquet format**: Columnar storage for time series
2. **Metadata embedded**: In parquet custom metadata (JSON)
3. **Repository protocol**: Defines persistence interface
4. **Sensor metadata**: name, height, orientation, type
5. **Julia integration**: File-based (parquet in/out)

### Red Flags
- Separate metadata files (.json sidecars)
- Direct polars/pandas in domain layer
- Memory-based Julia integration
- Metadata without versioning

### Approval Criteria
- Parquet as primary storage format
- Metadata embedded in parquet files
- Repository protocol separates concerns
- Sensor metadata is comprehensive

## Checklist
Before approving the plan, verify:
- [ ] Design aligns with ADR constraints
- [ ] Metadata embedded in parquet
- [ ] Repository protocol defined
- [ ] No direct polars in domain
- [ ] Julia integration via files
- [ ] Review comments are resolved
