---
id: ddd-t-002-entities-value-objects
name: entities-value-objects
description: DDD Entity vs Value Object classification criteria
tags: [ddd, tactical, entity, value-object]
applies_when:
  - deciding folder placement
  - modeling domain objects
  - refactoring misclassified objects
---

# DDD-T-002: Entities vs Value Objects

## Status

**Accepted**

## Context

DDD distinguishes two fundamental object types with different characteristics and lifecycles. Misclassification leads to:

- Wrong folder placement
- Incorrect equality semantics
- Improper caching strategies
- Confusion about mutability expectations

Current codebase has architectural debt with Entities misplaced in the `value_objects/` folder.

## Decision

### 1. ENTITY

**Definition**: Objects with identity that persists across state changes.

**Characteristics**:

- Has identity beyond attribute values
- Equality based on identity, not attributes
- Has lifecycle (created, modified, deleted)
- Mutable (state changes, identity remains)

**Folder**: `entities/`

**Identification Questions**:

- If I change all attributes, is it still the same object? → Entity
- Do I track this object over time? → Entity
- Does it have a unique ID or hash? → Entity

**CleanMast Examples**:

```python
# ✅ CORRECT: ReportAtom is an Entity
@dataclass
class ReportAtom:
    df: pl.DataFrame
    _df_hashkey: str  # Identity from content hash

    def __eq__(self, other):
        return self._df_hashkey == other._df_hashkey  # Identity equality

# Location: entities/report_atom.py ✅
```

### 2. VALUE OBJECT

**Definition**: Objects defined entirely by their attributes, with no identity.

**Characteristics**:

- No identity beyond attribute values
- Equality based on all attributes
- Immutable (frozen dataclass)
- Interchangeable if attributes equal

**Folder**: `value_objects/`

**Identification Questions**:

- If I change any attribute, is it a different object? → Value Object
- Can I replace it with another having same values? → Value Object
- Does it represent a description, amount, or range? → Value Object

**CleanMast Examples**:

```python
# ✅ CORRECT: Mast metadata is a Value Object
@dataclass(frozen=True)
class SingleMastMeta:
    mast_name: str
    caption: str
    width: str = "80%"

# Two instances with same values are equal:
meta1 = SingleMastMeta("M01", "Title")
meta2 = SingleMastMeta("M01", "Title")
assert meta1 == meta2  # True - value equality

# Location: value_objects/meta.py ✅
```

### 3. FOLDER STRUCTURE RULES

```
subdomains/{subdomain}/
├── entities/
│   ├── aggregate_root.py
│   ├── single_mast/           # NEW - concrete entities
│   │   ├── monthly_wind.py
│   │   └── wind_rose.py
│   └── collections/
│       └── atom_collection.py
│
└── value_objects/
    ├── single_mast/
    │   ├── schemas.py          # Value objects
    │   └── meta.py             # Value objects
    └── rep_ts_report_config.py
```

**Rule**: Entities go in `entities/`, Value Objects go in `value_objects/`. No exceptions.

### 4. CURRENT MISMATCHES (To Fix)

| File | Current Location | Should Be | Type |
|------|-----------------|-----------|------|
| `monthly_wind_power.py` | `value_objects/single_mast/` | `entities/single_mast/` | Entity |
| `wind_rose.py` | `value_objects/single_mast/` | `entities/single_mast/` | Entity |
| `atom_collection.py` | `value_objects/collections/` | `entities/collections/` | Entity |

## Rationale (WHY)

- **Correct Semantics**: Entities and Value Objects have fundamentally different behaviors
- **Equality Rules**: Entities use identity equality; Value Objects use value equality
- **Lifecycle Management**: Entities track changes over time; Value Objects are replaced
- **Performance**: Value Objects can be cached and shared; Entities cannot

## Consequences

### Positive

- Clear classification rules
- Consistent folder structure
- Correct equality semantics
- Proper caching strategies

### Negative

- Requires refactoring existing code
- Need to update imports
- May require changes to serialization logic

## Anti-Patterns (AVOID)

```python
# ❌ Entity in value_objects/
# value_objects/single_mast/monthly_wind_power.py
@dataclass
class MonthlyWindPowerAtom(ReportAtom[...]):  # Entity!
    ...

# ✅ Entity in entities/
# entities/single_mast/monthly_wind_power.py
@dataclass
class MonthlyWindPowerAtom(ReportAtom[...]):  # Correct location
    ...
```

## References

- Evans, E. "Domain-Driven Design" Chapter 5
- [ddd-t-001-aggregates.md](ddd-t-001-aggregates.md)
