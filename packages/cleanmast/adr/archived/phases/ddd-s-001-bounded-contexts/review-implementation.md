# Phase: Review-Implementation - Bounded Contexts

## When to Use
Load this file when reviewing code implementation for bounded contexts.

## Related ADR
- Main ADR: `adr/ddd-s-001-bounded-contexts.md` (verify strict compliance)

## Code Review Guidance

### Key Review Areas
- Context isolation - no direct imports
- Naming convention - PascalCase contexts
- Shared kernel - only TimeSeriesData
- Physical structure - separate packages

### Code Quality Checks
- Each context has own package
- No circular imports
- Shared types are minimal
- Context boundaries are respected

### ADR Compliance Verification
- [ ] 6 contexts implemented
- [ ] Context names in PascalCase
- [ ] TimeSeriesData in shared/ only
- [ ] No direct cross-context imports
- [ ] Physical isolation maintained

## Checklist
Before approving implementation, verify:
- [ ] Code matches approved plan
- [ ] ADR constraints are strictly followed
- [ ] All contexts properly structured
- [ ] No cross-context coupling
- [ ] Tests are comprehensive and pass
- [ ] Code review comments are addressed
