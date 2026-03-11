# Phase: Code - Subdomain Layout

## When to Use
Load this file during the implementation phase when organizing code structure.

## Related ADR
- Main ADR: `adr/structure-001-subdomain-layout.md` (follow constraints strictly)

## Implementation Guidance

### Key Implementation Steps
1. Create `src/subdomains/` directory
2. For each context, create: `subdomains/`, `application/`, `infrastructure/`
3. In subdomains/, create subdirectories by capability
4. Add `__init__.py` files with proper exports
5. Create `shared/` for cross-context types
6. Create `protocols/` for shared interfaces

### Example Structure
```python
src/subdomains/
├── dataingestion/
├── dataprocessing/
├── analysis/
├── reporting/
├── configuration/
└── pipeline/
```

### Domain Layer Rules
- NO imports of polars, pandas, requests, etc.
- Pure Python dataclasses
- Business logic only
- Protocol imports only

## Checklist
Before marking implementation complete, verify:
- [ ] Folder structure matches ADR
- [ ] Domain layer has no I/O imports
- [ ] All contexts follow same pattern
- [ ] __init__.py files with exports
- [ ] shared/ and protocols/ created
- [ ] Tests organized by context
