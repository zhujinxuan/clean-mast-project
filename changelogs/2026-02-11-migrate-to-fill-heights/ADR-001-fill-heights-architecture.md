# ADR-001: fill-heights Module Architecture

## Status
Accepted

## Context
The old `extrapolate` module was limited to simple power-law extrapolation. We needed a more comprehensive solution that handles:
- Multiple filling strategies (extrapolate, interpolate)
- Different sensor types (WindSpeed, WindDirection)
- Better configuration management
- Cleaner CLI structure

## Decision
Create a new `fill_heights` module with clear separation of concerns:

```
fill_heights/
├── commands/          # CLI command implementations
├── config.py         # Configuration models
├── execute/          # Execution layer (apply fills)
├── recommend/        # Planning layer (generate configs)
│   ├── planner.py   # Config generation
│   ├── validation.py # Runtime validation
│   └── fitting.py   # Parameter fitting
└── cli.py           # Thin CLI wrapper
```

## Consequences

### Positive
- Clear separation between planning and execution
- Testable components
- Extensible for new strategies
- Type-safe with Pydantic models

### Negative
- More files to maintain
- Learning curve for new structure

## Alternatives Considered
1. **Extend extrapolate**: Would create a monolithic module
2. **Keep both modules**: Would cause confusion
3. **Merge into single file**: Would reduce maintainability

## References
- Plan: `.sisyphus/plans/fill-heights-implementation.md`
