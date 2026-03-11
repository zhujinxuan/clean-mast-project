# Phase: On-Plan - Subdomain Layout

## When to Use
Load this file during the planning/design phase when organizing folder structure.

## Related ADR
- Main ADR: `adr/structure-001-subdomain-layout.md` (load first for constraints)

## Design Guidance

### Layer Organization

Each context follows this structure:
```
ContextName/
├── subdomains/           # Domain layer - pure business logic
│   └── {subdomain}/
│       ├── entities/     # Business objects with identity
│       ├── value_objects/# Immutable values
│       ├── domain_events/# Events for cross-boundary communication
│       └── domain_services/ # Stateless operations
├── application/          # Application layer - use cases
│   └── {use_case}.py     # Orchestrate domain operations
└── infrastructure/       # Infrastructure layer - I/O
    ├── repositories/     # Repository implementations
    └── external/         # External API clients
```

### Key Considerations
- Domain layer has NO external dependencies (no polars, no pandas)
- Application layer coordinates domain operations
- Infrastructure contains all I/O and external concerns
- Protocols define interfaces between layers

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
    data: pl.DataFrame
    sensors: list[SensorColumn]
```

Note: In DDD, Aggregate Roots ARE Entities. Both belong in the `entities/` folder.

### Subdomain Examples
- **DataIngestion**: parsing, loading, validation subdomains
- **DataProcessing**: cleaning, reconstruction subdomains
- **Analysis**: calculations, aggregations subdomains

## Checklist
Before proceeding to implementation, verify:
- [ ] Folder structure follows 3-layer architecture
- [ ] Domain layer is dependency-free
- [ ] Subdomains identified for each context
- [ ] Protocol location planned
- [ ] ADR constraints are respected
