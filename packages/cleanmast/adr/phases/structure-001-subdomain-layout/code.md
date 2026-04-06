# Phase: Code - Subdomain Layout

## When to Use
Load this file during the implementation phase when organizing code structure.

## Related ADR
- Main ADR: `adr/structure-001-subdomain-layout.md` (follow constraints strictly)

## Implementation Guidance

### Key Implementation Steps
1. Create `src/subdomains/` directory
2. Create context directories based on complexity needs
3. Add DDD folders appropriate for chosen pattern
4. Add `__init__.py` files with proper exports
5. Create `shared/` for cross-context types
6. Create `protocols/` for shared interfaces (layered pattern)

### Example Structure
```python
src/subdomains/
├── assessment/        # Layered pattern (3-layer)
├── dataingestion/     # Organized-flat pattern
├── dataprocessing/    # Minimal-flat pattern (CQRS naming)
├── configuration/     # Minimal-flat pattern
└── pipeline/          # Minimal-flat pattern
```

### Pattern Selection Guide
- **Layered**: Complex subdomains with multiple application services (assessment)
- **Organized-flat**: Moderate complexity with repositories (dataingestion)
- **Minimal-flat**: Simple subdomains with basic entities (configuration, pipeline)

### Domain Layer Rules
- NO imports of polars, pandas, requests, etc.
- Pure Python dataclasses
- Business logic only
- Protocol imports only (layered pattern)

## Checklist
Before marking implementation complete, verify:
- [ ] Folder structure matches ADR
- [ ] Domain layer has no I/O imports
- [ ] Pattern appropriate for context complexity
- [ ] __init__.py files with exports
- [ ] shared/ and protocols/ created (if needed)
- [ ] Tests organized by context
