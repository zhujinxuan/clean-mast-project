# Phase: Review-Plan - Subdomain Layout

## When to Use
Load this file when reviewing a design/plan for folder structure.

## Related ADR
- Main ADR: `adr/structure-001-subdomain-layout.md` (verify compliance)

## Review Guidance

### Key Review Points
1. **3-layer architecture**: Domain, Application, Infrastructure
2. **Domain purity**: No external dependencies in subdomains/
3. **Subdomain organization**: By business capability
4. **Protocol location**: interfaces in domain/protocols/
5. **Context isolation**: No cross-context references

### Red Flags
- Infrastructure code in domain layer
- Missing subdomain separation
- Direct imports between contexts
- Protocols in wrong location

### Approval Criteria
- Layer separation is clear
- Domain layer is pure Python
- Subdomains organized by capability
- Protocols properly placed

## Checklist
Before approving the plan, verify:
- [ ] Design aligns with ADR constraints
- [ ] 3-layer architecture respected
- [ ] Domain layer purity maintained
- [ ] Subdomains properly identified
- [ ] Protocols in correct location
- [ ] Review comments are resolved
