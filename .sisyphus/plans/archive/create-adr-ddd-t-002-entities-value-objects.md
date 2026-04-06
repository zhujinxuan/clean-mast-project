# Work Plan: Create ADR ddd-t-002-entities-value-objects

## TL;DR

Create Architecture Decision Record defining **Entity vs Value Object** classification with clear criteria and folder structure.

**Why**: Codebase has misplaced atoms (Entities in `value_objects/` folder). Need clear rules to prevent this.

**File**: `packages/cleanmast/adr/ddd-t-002-entities-value-objects.md`

---

## Context

Current codebase has architectural debt:
- `monthly_wind_power.py` - Entity in `value_objects/` ❌
- `wind_rose.py` - Entity in `value_objects/` ❌
- `atom_collection.py` - Entity in `value_objects/` ❌

All should be in `entities/` folder per DDD.

Need ADR to establish:
1. Clear classification criteria
2. Folder structure rules
3. How to identify each type

---

## Work Objectives

### Deliverable
Single ADR file with:
- Entity definition and criteria
- Value Object definition and criteria
- Folder structure rules
- CleanMast examples showing correct/incorrect placement

---

## Execution Strategy

Single task - documentation.

---

## Task Dependency Graph

| Task | Depends On | Reason |
|------|-----------|--------|
| 1. Create ddd-t-002-entities-value-objects | ddd-t-001 | Builds on Aggregate concept |

---

## TODOs

- [x] 1. Create ADR ddd-t-002-entities-value-objects

  **What to do**:
  Create `packages/cleanmast/adr/ddd-t-002-entities-value-objects.md`:

  ```yaml
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
  ```

  **Required Sections**:

  ### Status
  **Accepted**

  ### Context
  DDD distinguishes two fundamental object types with different characteristics and lifecycles. Misclassification leads to:
  - Wrong folder placement
  - Incorrect equality semantics
  - Improper caching strategies

  ### Decision

  **1. ENTITY**

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

  **2. VALUE OBJECT**

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
  - Does it represent a description/amount/range? → Value Object

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

  **3. FOLDER STRUCTURE RULES**

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

  **4. CURRENT MISMATCHES (To Fix)**

  | File | Current Location | Should Be | Type |
  |------|-----------------|-----------|------|
  | `monthly_wind_power.py` | `value_objects/single_mast/` | `entities/single_mast/` | Entity |
  | `wind_rose.py` | `value_objects/single_mast/` | `entities/single_mast/` | Entity |
  | `atom_collection.py` | `value_objects/collections/` | `entities/collections/` | Entity |

  ### Consequences

  **Positive**:
  - Clear classification rules
  - Consistent folder structure
  - Correct equality semantics

  **Negative**:
  - Requires refactoring existing code
  - Need to update imports

  ### Anti-Patterns

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

  ### References
  - Evans, E. "Domain-Driven Design" Chapter 5
  - ddd-t-001-aggregates

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: ddd-t-003, refactoring plans
  - **Blocked By**: ddd-t-001

  **Acceptance Criteria**:
  - [ ] Clear Entity definition with criteria
  - [ ] Clear Value Object definition with criteria
  - [ ] Folder structure rules
  - [ ] CleanMast examples (correct and incorrect)
  - [ ] Current mismatches documented

  **QA Scenario**:
  ```
  Scenario: ADR provides classification guidance
    Tool: Bash
    Steps:
      1. grep -A 5 "Identification Questions" packages/cleanmast/adr/ddd-t-002-entities-value-objects.md
      2. grep "value_objects/" packages/cleanmast/adr/ddd-t-002-entities-value-objects.md
    Expected: Shows decision tree, shows current mismatches table
    Evidence: Terminal output
  ```

  **Commit**: YES
  - Message: `docs(adr): add ddd-t-002-entities-value-objects classification`
  - Files: `packages/cleanmast/adr/ddd-t-002-entities-value-objects.md`

---

## Success Criteria

- [ ] Entity criteria clear (identity, lifecycle, mutability)
- [ ] Value Object criteria clear (no identity, immutable, value equality)
- [ ] Folder rules documented
- [ ] Current mismatches identified
- [ ] Examples from CleanMast codebase
