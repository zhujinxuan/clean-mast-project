# Phase: Code - Bounded Contexts

## When to Use
Load this file during the implementation phase when coding bounded contexts.

## Related ADR
- Main ADR: `adr/ddd-s-001-bounded-contexts.md` (follow constraints strictly)

## Implementation Guidance

### Key Implementation Steps
1. Create `src/subdomains/` directory
2. Create 6 subdomain packages: `configuration/`, `pipeline/`, `dataingestion/`, `dataprocessing/`, `analysis/`, `reporting/`
3. Each context gets `subdomains/`, `application/`, `infrastructure/`
4. Define `shared/types.py` with TimeSeriesData
5. Set up `__init__.py` exports for each context

### Folder Structure Example
```python
src/subdomains/
├── configuration/
├── pipeline/
├── dataingestion/
├── dataprocessing/
├── analysis/
└── reporting/
```

### Testing Strategy
- Test each context in isolation
- Mock other contexts when testing
- Integration tests only at PipelineContext level

## Checklist
Before marking implementation complete, verify:
- [ ] Code follows ADR patterns
- [ ] 6 context packages exist
- [ ] Each context has proper structure
- [ ] Shared types in shared/types.py
- [ ] No cross-context imports
- [ ] Tests pass for each context
