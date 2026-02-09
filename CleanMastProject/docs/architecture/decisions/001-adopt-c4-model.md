# ADR-001: Adopt C4 Model for Documentation

## Status

Accepted

## Context

The project needs a consistent approach to documenting software architecture that is:
- Accessible to both technical and non-technical stakeholders
- Hierarchical, from high-level context to implementation details
- Easy to maintain and update as the system evolves

Current documentation is fragmented across multiple directories without a unified structure.

## Decision

Adopt the C4 model (Context, Containers, Components, and Code) as the primary documentation structure for CleanMast.

The documentation hierarchy will be:
- **Context diagrams**: User perspective, showing system boundaries and external dependencies
- **Container diagrams**: Technology choices (Julia/Python packages, CLI tools)
- **Component diagrams**: Internal structure of major modules
- **Code diagrams**: Class/module relationships (optional, for complex areas)

## Consequences

**Benefits:**
- Consistent structure for all architectural documentation
- Multiple levels of abstraction for different audiences
- Clear separation between user-facing and developer-facing documentation
- Easier navigation and maintenance

**Trade-offs:**
- Initial effort to reorganize existing documentation
- Requires learning C4 notation for new diagrams
- Additional maintenance burden to keep diagrams updated

## Alternatives Considered

- **ASCII diagrams only**: Less expressive, harder to maintain consistency
- **PlantUML**: More powerful but steeper learning curve
- **Keep existing ad-hoc structure**: No improvement in discoverability or consistency

## References

- [C4 Model](https://c4model.com/)
- [Structurizr](https://structurizr.com/) - C4 tooling
- Project documentation: [docs/architecture/](../README.md)
