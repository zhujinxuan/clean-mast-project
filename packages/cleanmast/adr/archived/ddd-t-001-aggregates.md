---
id: ddd-t-001-aggregates
name: aggregates
description: DDD Aggregate pattern with Aggregate Root
tags: [ddd, tactical, aggregate, entity]
applies_when:
  - defining consistency boundaries
  - creating aggregate roots
  - refactoring entity clusters
---

# DDD-T-001: Aggregates

## Status

**Accepted**

## Context

Complex domain models have interconnected objects. We need consistency boundaries to:

- Protect invariants across related objects
- Define transaction boundaries
- Control cascading changes
- Simplify the object graph for clients

Without aggregates, any object could be modified directly, leading to inconsistent states and broken business rules.

## Decision

### 1. Aggregate Definition

An Aggregate is a cluster of associated objects treated as a single unit for data changes. External objects may only reference the Aggregate Root. The root protects the internal consistency of the aggregate.

### 2. Aggregate Root Characteristics

The Aggregate Root is an Entity with these properties:

- **Identity**: It has identity beyond attribute values
- **Access Control**: All external references go through the root
- **Invariant Protection**: Root enforces invariants across the entire aggregate
- **Lifecycle Control**: Root manages creation and deletion of child objects

### 3. Folder Structure

```
src/subdomains/{context}/subdomains/{subdomain}/
├── entities/
│   ├── aggregate_root.py          # The root entity
│   └── related_entities/          # Other entities in aggregate
│       └── child_entity.py        # Referenced only via root
└── value_objects/
    └── measurements.py            # Value objects used by aggregate
```

**Note**: Aggregate Roots ARE Entities. They belong in the `entities/` folder, not a separate `aggregates/` folder. See [structure-001-subdomain-layout.md](structure-001-subdomain-layout.md).

### 4. Identification Rules

An object IS an Aggregate Root if:

- It has identity independent of attribute values
- It controls the lifecycle of child objects
- It enforces invariants across the cluster
- External objects reference it (not its children directly)
- It serves as the consistency boundary for transactions

### 5. CleanMast Examples

| Aggregate | Root | Children | Location |
|-----------|------|----------|----------|
| Report | ReportAtom | (none - simple aggregate) | `entities/report_atom.py` |
| Mast Analysis | MastAnalyzer | Sensors, TimeSeries | `entities/mast/` |

## Rationale (WHY)

- **Consistency Boundaries**: Clear transaction boundaries simplify persistence
- **Encapsulation**: Internal details hidden from external code
- **Simplified Repository Pattern**: One repository per aggregate root
- **Performance**: Smaller aggregates load faster; large aggregates hurt performance

## Consequences

### Positive

- Clear consistency boundaries make transactions explicit
- Simplified repository pattern (one repo per aggregate)
- Encapsulation protects domain invariants
- Easier to reason about object relationships

### Negative

- May need refactoring if boundaries are wrong
- Large aggregates hurt performance (load entire graph)
- Cross-aggregate rules require eventual consistency

## Anti-Patterns (AVOID)

```python
# ❌ Child entity referenced directly from outside
sensor = Sensor.find(sensor_id)
sensor.calibrate()  # Don't do this - breaks aggregate boundary

# ❌ Repository for non-root entity
class SensorRepository:  # Don't do this
    def save(self, sensor: Sensor): ...

# ✅ Go through aggregate root
mast = MastRepository.find(mast_id)
mast.get_sensor(sensor_id).calibrate()  # Do this

# ✅ Repository only for aggregate root
class MastRepository:  # Do this
    def save(self, mast: MastAnalyzer): ...
```

## References

- Evans, E. "Domain-Driven Design" Chapter 6 - Aggregates
- Vernon, V. "Implementing Domain-Driven Design" Chapter 10 - Aggregates
- [structure-001-subdomain-layout.md](structure-001-subdomain-layout.md) - Folder structure for entities
