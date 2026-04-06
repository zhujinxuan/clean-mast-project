# Work Plan: Create ADR ddd-t-001-aggregates

## TL;DR

Create Architecture Decision Record defining **Aggregate** pattern in DDD - clusters of entities treated as a single unit with an Aggregate Root.

**Why**: Referenced throughout codebase but ADR doesn't exist. Need formal definition before refactoring misplaced atoms.

**File**: `packages/cleanmast/adr/ddd-t-001-aggregates.md`

---

## Context

The codebase references `ddd-t-001-aggregates` in multiple files but the ADR doesn't exist:
- `report_atom.py`: `"ADR-GUARDRAILS: ... ddd-t-001-aggregates"`
- `wind_rose.py`: `"ADR-GUARDRAILS: ... ddd-t-001-aggregates"`

We need this ADR to establish:
1. What is an Aggregate
2. What is an Aggregate Root (Entity)
3. Folder structure: Aggregates go in `entities/`
4. How to identify Aggregate boundaries

---

## Work Objectives

### Deliverable
Single ADR file with:
- Definition of Aggregate pattern
- Aggregate Root characteristics
- Folder structure rules
- Examples from CleanMast

### Must Include
1. **Status**: Accepted
2. **Context**: Why aggregates matter (consistency boundaries)
3. **Decision**: Rules for aggregate design
4. **Consequences**: Pros/cons
5. **Examples**: ReportAtom as Aggregate Root

---

## Execution Strategy

Single task - documentation only.

---

## Task Dependency Graph

| Task | Depends On | Reason |
|------|-----------|--------|
| 1. Create ddd-t-001-aggregates | None | Independent |

---

## TODOs

- [x] 1. Create ADR ddd-t-001-aggregates

  **What to do**:
  Create `packages/cleanmast/adr/ddd-t-001-aggregates.md` with:

  ```yaml
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
  ```

  **Required Sections**:

  ### Status
  **Accepted**

  ### Context
  Complex domain models have interconnected objects. We need consistency boundaries to:
  - Protect invariants across related objects
  - Define transaction boundaries
  - Control cascading changes

  ### Decision

  **1. Aggregate Definition**
  An Aggregate is a cluster of associated objects treated as a single unit for data changes.

  **2. Aggregate Root (Entity)**
  - One entity serves as the Aggregate Root
  - All external references go through the root
  - Root protects invariants of the whole aggregate
  - Has identity (not defined by attributes)

  **3. Folder Structure**
  ```
  entities/
  ├── aggregate_root.py          # The root entity
  └── related_entities/          # Other entities in aggregate
      └── child_entity.py        # Referenced only via root
  ```

  **4. Identification Rules**
  An object IS an Aggregate Root if:
  - It has identity beyond attribute values
  - It controls lifecycle of child objects
  - It enforces invariants across the cluster
  - External objects reference it (not children)

  **5. CleanMast Examples**

  | Aggregate | Root | Children | Location |
  |-----------|------|----------|----------|
  | Report | ReportAtom | (none - simple aggregate) | `entities/report_atom.py` |
  | Mast Analysis | MastAnalyzer | Sensors, TimeSeries | `entities/mast/` |

  ### Consequences

  **Positive**:
  - Clear consistency boundaries
  - Simplified repository pattern (one repo per aggregate)
  - Transaction boundaries are explicit

  **Negative**:
  - May need to refactor if boundaries wrong
  - Large aggregates hurt performance

  ### Anti-Patterns
  ```python
  # ❌ Child entity referenced directly from outside
  sensor.calibrate()  # Don't do this

  # ✅ Go through aggregate root
  mast.get_sensor(id).calibrate()  # Do this
  ```

  ### References
  - Evans, E. "Domain-Driven Design" Chapter 6
  - Vernon, V. "Implementing Domain-Driven Design" Chapter 10

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: ddd-t-002, ddd-t-003
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] YAML frontmatter valid
  - [ ] All sections present
  - [ ] Examples from CleanMast codebase
  - [ ] Anti-patterns documented
  - [ ] References to DDD literature

  **QA Scenario**:
  ```
  Scenario: ADR format correct
    Tool: Bash
    Steps:
      1. head -30 packages/cleanmast/adr/ddd-t-001-aggregates.md
      2. grep "^id:" packages/cleanmast/adr/ddd-t-001-aggregates.md
      3. grep "^## " packages/cleanmast/adr/ddd-t-001-aggregates.md
    Expected: YAML header, then sections: Status, Context, Decision, Consequences
    Evidence: Terminal output
  ```

  **Commit**: YES
  - Message: `docs(adr): add ddd-t-001-aggregates pattern`
  - Files: `packages/cleanmast/adr/ddd-t-001-aggregates.md`

---

## Success Criteria

- [ ] ADR file created
- [ ] Format matches existing ADRs
- [ ] Clear definition of Aggregate Root
- [ ] Folder structure rules documented
- [ ] CleanMast examples included
