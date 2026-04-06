# ADR ddd-t-002-entities-value-objects Created

## Summary
Successfully created Entity vs Value Object classification ADR.

## Key Patterns Established
- Entity: identity-based equality, mutable, has lifecycle
- Value Object: attribute-based equality, immutable, interchangeable
- Clear folder rules: entities/ vs value_objects/

## Current Mismatches Documented
- monthly_wind_power.py (Entity in value_objects/)
- wind_rose.py (Entity in value_objects/)
- atom_collection.py (Entity in value_objects/)

## Observations
- The AtomCollection file already references this ADR in its header (forward reference)
- Structure follows ddd-t-001-aggregates format for consistency
- Examples use actual CleanMast codebase patterns (ReportAtom, SingleMastMeta)

