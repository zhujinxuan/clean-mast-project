# Architecture Decision Records (ADRs)

This directory contains ADRs - significant architectural decisions made for the CleanMast project.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures important architectural decisions along with their context and consequences. ADRs help team members understand why certain decisions were made and provide a historical record for future reference.

## ADR Format

See [ADR-template.md](ADR-template.md) for the standard format. Each ADR includes:
- **Status**: Proposed, Accepted, Deprecated, or Superseded
- **Context**: The problem or situation motivating the decision
- **Decision**: The actual change or choice made
- **Consequences**: The outcomes (positive, negative, and neutral)
- **Alternatives Considered**: Other options and why they were rejected
- **References**: Related documentation and resources

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [001](001-adopt-c4-model.md) | Adopt C4 Model for Documentation | Accepted |
| [002](002-parquet-migration.md) | Migrate from CSV+TOML to Parquet Format | Accepted |

## Creating New ADRs

1. Copy [ADR-template.md](ADR-template.md) to a new file with the next sequential number
2. Fill in all sections with appropriate content
3. Add the new ADR to this index
4. Commit the changes

## Related Documentation

- [Documentation Hub](../../README.md) - Main documentation entry point
- [C4 Architecture Documentation](../c4/) - System architecture diagrams
- [Technical Documentation](../technical/) - Algorithm implementation details
- [Development Documentation](../development/) - Developer guides
