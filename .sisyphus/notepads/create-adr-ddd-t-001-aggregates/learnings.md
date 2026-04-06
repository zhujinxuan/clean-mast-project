## ADR Creation - ddd-t-001-aggregates

**Completed**: 2025-03-13
**File**: packages/cleanmast/adr/ddd-t-001-aggregates.md

### What Was Created
- DDD Aggregate pattern ADR with full YAML frontmatter
- Constraint/Rationale/Anti-Pattern format matching existing ADRs
- All required sections: Status, Context, Decision, Consequences, Anti-Patterns, References
- CleanMast examples table (ReportAtom, MastAnalyzer)
- Code examples showing anti-patterns and correct usage

### Key Design Decisions
- Followed structure-001 format with Constraint/Rationale/Anti-Pattern sections
- Referenced structure-001 for folder placement (entities/ not aggregates/)
- Used DDD-T-* prefix for tactical patterns (consistent with ddd-s-* for strategic)
- Included specific CleanMast examples from codebase references

### References Added
- Evans DDD Chapter 6 (Aggregates)
- Vernon IDDD Chapter 10 (Aggregates)
- Cross-reference to structure-001-subdomain-layout.md

### Format Pattern for Future ADRs
```markdown
---
id: ddd-t-XXX-name
name: name
description: Brief description
tags: [ddd, tactical, ...]
applies_when:
  - condition 1
  - condition 2
---

# DDD-T-XXX: Title

## Status
**Accepted**

## Context
Why this matters...

## Decision

### 1. Pattern Definition
...

### 2. Rules/Characteristics
...

## Rationale (WHY)
...

## Consequences

### Positive
...

### Negative
...

## Anti-Patterns (AVOID)
```python
# ❌ Don't do this
bad_code()

# ✅ Do this
good_code()
```

## References
- Book/Resource reference
- Cross-reference to other ADR
```
