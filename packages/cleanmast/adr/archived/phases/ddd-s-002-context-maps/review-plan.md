# Phase: Review-Plan - Context Maps

## When to Use
Load this file when reviewing a design/plan for context relationships.

## Related ADR
- Main ADR: `adr/ddd-s-002-context-maps.md` (verify compliance)

## Review Guidance

### Key Review Points
1. **6 relationships documented**: All context pairs accounted for
2. **Pattern selection**: Customer-Supplier vs Conformist correctly chosen
3. **Repository protocol**: Defined for DataIngestion → DataProcessing
4. **No circular deps**: All arrows point one direction
5. **PipelineContext**: Orchestrates without tight coupling

### Red Flags
- Circular dependencies in diagram
- Missing relationship documentation
- Direct service calls instead of protocols
- Reporting trying to change Analysis format

### Approval Criteria
- Context map diagram exists
- All relationships use appropriate patterns
- Repository protocol is defined
- Integration points are explicit

## Checklist
Before approving the plan, verify:
- [ ] Design aligns with ADR constraints
- [ ] All context relationships documented
- [ ] Repository protocol defined
- [ ] No circular dependencies
- [ ] Integration points are clear
- [ ] Review comments are resolved
