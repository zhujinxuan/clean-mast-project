# Phase: Review-Plan - Bounded Contexts

## When to Use
Load this file when reviewing a design/plan for bounded contexts before implementation.

## Related ADR
- Main ADR: `adr/ddd-s-001-bounded-contexts.md` (verify compliance)

## Review Guidance

### Key Review Points
1. **Context count**: Exactly 6 contexts defined
2. **Clear boundaries**: Each context has distinct, non-overlapping responsibilities
3. **PascalCase naming**: `DataIngestion` not `data-ingestion`
4. **Shared kernel**: Only TimeSeriesData as DTO
5. **No direct imports**: Between contexts - protocols only

### Red Flags
- More than 6 contexts (over-engineering)
- Fewer than 6 contexts (missing capabilities)
- Context names with hyphens or underscores
- Shared kernel with business logic
- Direct cross-context references in design

### Approval Criteria
- All 6 contexts identified with clear ownership
- TimeSeriesData is the only shared type
- Physical isolation plan (separate packages)
- No circular dependencies in design

## Checklist
Before approving the plan, verify:
- [ ] Design aligns with ADR constraints
- [ ] All 6 contexts are present
- [ ] Context names follow PascalCase
- [ ] Shared kernel is minimal
- [ ] Dependencies are documented
- [ ] Review comments are resolved
