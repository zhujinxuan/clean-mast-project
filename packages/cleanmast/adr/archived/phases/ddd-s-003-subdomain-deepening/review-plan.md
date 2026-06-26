# Phase: Review-Plan - Subdomain Deepening

## When to Use
Load this file when reviewing a design/plan for nested subdomain decomposition.

## Related ADR
- Main ADR: `adr/ddd-s-003-subdomain-deepening.md` (verify compliance)

## Review Guidance

### Key Review Points
1. **Directory structure**: Proposed directories follow Nested Subdomain pattern
2. **Import isolation**: Planned imports respect subdomain isolation rules
3. **Per-domain ADRs**: Each new subdomain has a planned per-domain ADR
4. **shared/ purity**: shared/ contains only protocols, ir_types, and utils

### Pattern Acceptance
Nested subdomain decomposition is required when:
- A domain has more than 5 independent capability groups
- Sections or entities are flat and cross-import freely
- A single domain's ADR exceeds ~40 lines

### Red Flags
- Cross-subdomain imports in planned module dependencies
- Concrete implementations planned for shared/ directory
- Missing per-domain ADR for any new subdomain
- Adapters/ directory containing anything other than protocol implementations

### Approval Criteria
- Directory layout matches `shared/`, `adapters/`, `subdomains/{name}/` pattern
- Import graph shows subdomain → shared/ + parent adapters/ + self only
- Every planned subdomain has a corresponding per-domain ADR
- shared/ directory contains no concrete business logic

## Checklist
Before approving the plan, verify:
- [ ] Proposed directories follow Nested Subdomain pattern (shared/, adapters/, subdomains/{name}/entities|services|value_objects/)
- [ ] Planned imports respect subdomain isolation (subdomain → shared/ + parent adapters/ + self only, no cross-subdomain)
- [ ] Per-domain ADR files planned for each new subdomain
- [ ] shared/ contains only protocols, ir_types, utils (no concrete implementations)
- [ ] Design aligns with ADR constraints
- [ ] Review comments are resolved
