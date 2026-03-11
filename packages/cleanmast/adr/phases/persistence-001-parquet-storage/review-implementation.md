# Phase: Review-Implementation - Parquet Storage

## When to Use
Load this file when reviewing code implementation for data persistence.

## Related ADR
- Main ADR: `adr/persistence-001-parquet-storage.md` (verify strict compliance)

## Code Review Guidance

### Key Review Areas
- Parquet format usage
- Metadata embedding
- Repository protocol separation
- No I/O in domain layer

### Code Quality Checks
- Metadata is JSON-serializable
- Parquet files readable by Julia
- Repository handles errors gracefully
- Version included in metadata

### ADR Compliance Verification
- [ ] Parquet format used
- [ ] Metadata embedded
- [ ] Repository protocol defined
- [ ] No polars in domain
- [ ] Julia integration via files

## Checklist
Before approving implementation, verify:
- [ ] Code matches approved plan
- [ ] ADR constraints are strictly followed
- [ ] Metadata properly embedded
- [ ] Tests pass
- [ ] Julia can read output
- [ ] Code review comments are addressed
