# Phase: Review-Plan - Subdomain Layout

## When to Use
Load this file when reviewing a design/plan for folder structure.

## Related ADR
- Main ADR: `adr/structure-001-subdomain-layout.md` (verify compliance)

## Review Guidance

### Key Review Points
1. **Pattern appropriateness**: Layered vs flat based on complexity
2. **Domain purity**: No external dependencies in domain layer
3. **Subdomain organization**: By business capability
4. **Protocol location**: interfaces in domain/protocols/ (layered pattern)
5. **Context isolation**: No cross-context references

### Pattern Acceptance
Flat patterns are acceptable for simpler subdomains:
- **Minimal-flat**: configuration, pipeline (entities/, services/ only)
- **Organized-flat**: dataingestion (entities/, repositories/, services/, value_objects/)
- **Layered**: assessment (full 3-layer with domain/application/infrastructure)

### Red Flags
- Infrastructure code in domain layer
- Missing subdomain separation
- Direct imports between contexts
- Protocols in wrong location (layered pattern)

### Approval Criteria
- Pattern matches subdomain complexity
- Domain layer is pure Python
- Subdomains organized by capability
- Protocols properly placed (if using layered pattern)

## Checklist
Before approving the plan, verify:
- [ ] Design aligns with ADR constraints
- [ ] Pattern appropriate for context complexity
- [ ] Domain layer purity maintained
- [ ] Subdomains properly identified
- [ ] Protocols in correct location (if layered)
- [ ] Review comments are resolved
- [ ] Nested Subdomain pattern proposed where appropriate (>5 independent capability groups within a single domain)
- [ ] Proposed shared/ directory contains only protocols, ir_types, utils (no concrete implementations planned)
- [ ] Proposed adapters/ directory contains only adapter implementations (not domain logic)
- [ ] Per-domain ADRs (adr-{adr-id}.md) planned for each new subdomain

## References
For detailed Nested Subdomain enforcement, see `ddd-s-003-subdomain-deepening.md` phases and `packages/cleanmast/.agents/skills/adr-guardrails-skill/review-plan.md`
