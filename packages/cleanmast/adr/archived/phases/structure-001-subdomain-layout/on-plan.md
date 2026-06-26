# Phase: On-Plan - Subdomain Layout

## When to Use
Load this file during the planning/design phase when organizing folder structure.

## Related ADR
- Main ADR: `adr/structure-001-subdomain-layout.md` (load first for constraints)

## Design Guidance

### Layer Organization

Contexts follow one of these patterns:

**Layered Pattern** (assessment):
```
assessment/
├── domain/               # Domain layer - pure business logic
│   ├── entities/         # Business objects with identity
│   ├── protocols/        # Interface definitions
│   ├── services/         # Domain services
│   └── value_objects/    # Immutable values
├── application/          # Application layer - use cases
│   └── services/
└── infrastructure/       # Infrastructure layer - I/O
```

**Flat Pattern** (dataingestion, configuration, dataprocessing, pipeline):
```
dataingestion/            # DDD folders without layer nesting
├── entities/
├── value_objects/
├── repositories/
├── services/
└── infrastructure/
```

### Key Considerations
- Domain layer has NO external dependencies (no polars, no pandas)
- Application layer coordinates domain operations (layered pattern only)
- Infrastructure contains all I/O and external concerns
- Protocols define interfaces between layers (layered pattern only)
- Flat patterns are acceptable for simpler subdomains

### Entity Examples

**Simple Entity** (business object with identity):
```python
# entities/sensor.py
@dataclass
class Sensor:
    """Domain Entity: A physical sensor on a mast."""
    id: SensorId
    height: float
    measurement_type: str
```

**Aggregate Root** (also an Entity):
```python
# entities/time_series.py
@dataclass
class TimeSeries:
    """Domain Entity (Aggregate Root): Time series data collection."""
    source: TimeSeriesSource  # identity part 1
    time_range: TimeRange     # identity part 2
    sensors: list[SensorColumn]
```

Note: In DDD, Aggregate Roots ARE Entities. Both belong in the `entities/` folder.

### Current Contexts
- **assessment**: Layered pattern (3-layer)
- **dataingestion**: Organized-flat pattern
- **dataprocessing**: Minimal-flat pattern (CQRS naming: commands/, strategies/)
- **configuration**: Minimal-flat pattern
- **pipeline**: Minimal-flat pattern

## Checklist
Before proceeding to implementation, verify:
- [ ] Folder structure follows appropriate pattern for complexity
- [ ] Domain layer is dependency-free
- [ ] Context pattern chosen (layered vs flat) based on needs
- [ ] Protocol location planned (if using layered pattern)
- [ ] ADR constraints are respected
