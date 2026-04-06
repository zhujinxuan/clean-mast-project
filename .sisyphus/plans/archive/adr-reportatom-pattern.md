# Work Plan: ADR for ReportAtom Pattern

## TL;DR

Create an Architecture Decision Record (ADR) documenting the **ReportAtom pattern** - the content-addressable, polymorphic rendering component used across the Reporting bounded context.

**Scope**: Single markdown file (`packages/cleanmast/adr/ddd-t-003-report-atoms.md`)

---

## Context

The CleanMast codebase uses a **ReportAtom** pattern for report components that:
- Store validated Polars DataFrames with dataframely schemas
- Compute content hashes (SHA256 of Parquet) for identity
- Provide 3 rendering interfaces: image, table, summary
- Compose into report sections via `AtomCollection`

This pattern needs formal documentation as an ADR following the existing `adr/` conventions.

---

## Work Objectives

### Deliverable
Single ADR file: `packages/cleanmast/adr/ddd-t-003-report-atoms.md`

### Must Include
1. **Status**: Proposed → Accepted (after implementation)
2. **Context**: Why atoms are needed (content-addressable, polymorphic rendering)
3. **Decision**: 
   - Pattern specification with code examples
   - **CRITICAL: ReportAtom IS AN ENTITY** (not Value Object)
   - Content-addressable identity via SHA256 hash
   - Concrete atoms belong in `entities/` folder
   - Only schemas/metadata are Value Objects in `value_objects/`
4. **Consequences**: Pros/cons and anti-patterns
5. **Current Mismatches**: Document atoms currently misplaced in `value_objects/`
6. **References**: Links to related ADRs and PRDs

### Definition of Done
```bash
# File exists and is readable
cat packages/cleanmast/adr/ddd-t-003-report-atoms.md

# Follows existing ADR format (see structure-001-subdomain-layout.md)
# Tagged correctly for discoverability
```

---

## Verification Strategy

No automated tests - this is documentation. Verification is:
- File renders correctly in markdown viewer
- Links to referenced ADRs exist
- Format matches existing ADRs (YAML frontmatter, sections)

---

## Execution Strategy

Single sequential task (documentation only):

### Wave 1: ADR Creation
- Task 1: Write ADR file

---

## TODOs

- [x] 1. Create ADR ddd-t-003-report-atoms.md

  **What to do**:
  - Create `packages/cleanmast/adr/ddd-t-003-report-atoms.md`
  - Copy YAML frontmatter format from existing ADRs
  - Document:
    * Content-addressable hashing rationale
    * Generic type parameters (T, M)
    * 3 rendering interfaces
    * AtomCollection composition
    * Domain-specific atom examples (25+ types)
    * Migration path from Julia
    * Anti-patterns
  - Add references to related ADRs and PRDs

  **Must NOT do**:
  - Include implementation code (only examples)
  - Make assumptions about future features

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Refactoring of misplaced atoms
  - **Blocked By**: None (can proceed independently)
  
  **Note on Dependencies**: 
  This ADR references ddd-t-001-aggregates and ddd-t-002-entities-value-objects for completeness.
  These ADRs are planned in separate work items but this ADR can be written independently.
  The classification rules (Entity vs Value Object) are documented within this ADR itself.

  **References**:
  - Existing ADR format: `packages/cleanmast/adr/structure-001-subdomain-layout.md`
  - ADR README: `packages/cleanmast/adr/README.md`
  - Current atom implementation: `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/report_atom.py`
  - Related ADRs (planned/in-progress): 
    - `ddd-t-001-aggregates` - Aggregate Root pattern (separate work item)
    - `ddd-t-002-entities-value-objects` - Entity vs VO classification (separate work item)
  - Existing ADRs:
    - `persistence-001-parquet-storage.md` - Parquet hashing
    - `structure-001-subdomain-layout.md` - Subdomain layout (covers Aggregate in entities/)
  - Note on Classification: 
    - ReportAtom and concrete atoms ARE ENTITIES (identity via content hash)
    - Currently MISPLACED in `value_objects/` - should be in `entities/`
    - Only `schemas.py`, `meta.py` are true Value Objects

  **Acceptance Criteria**:
  - [ ] File exists at correct path
  - [ ] Valid YAML frontmatter
  - [ ] All required sections present
  - [ ] Code examples compile (syntax check)
  - [ ] Links to existing ADRs verified

  **QA Scenarios**:
  ```
  Scenario: Verify ADR format
    Tool: Python (cross-platform)
    Steps:
      1. python -c "
         with open('packages/cleanmast/adr/ddd-t-003-report-atoms.md') as f:
             content = f.read()
         assert content.startswith('---')  # YAML frontmatter
         assert '## Status' in content
         assert '## Context' in content
         assert '## Decision' in content
         print('All sections present')
      "
    Expected Result: "All sections present"
    Evidence: Terminal output
  ```

  **Commit**: YES
  - Message: `docs(adr): add ddd-t-003-report-atoms pattern documentation`
  - Files: `packages/cleanmast/adr/ddd-t-003-report-atoms.md`
  - Pre-commit: None (documentation only)

---

## Final Verification Wave

- [ ] F1. **Plan Compliance Audit** - Verify file exists and matches format
- [ ] F2. **Documentation Quality** - Grammar, clarity, completeness
- [ ] F3. **Cross-Reference Check** - All linked ADRs exist
- [ ] F4. **Scope Fidelity** - No implementation, only patterns

---

## Commit Strategy

- **1**: `docs(adr): add ddd-t-003-report-atoms pattern documentation` - ADR file

---

## Success Criteria

- [ ] ADR file created and readable
- [ ] Format matches existing ADRs
- [ ] All 25+ atom types referenced
- [ ] Migration path documented
- [ ] Anti-patterns section complete
