# Phase: Review-Implementation - Subdomain Layout

## When to Use
Load this file when reviewing code implementation for folder structure.

## Related ADR
- Main ADR: `adr/structure-001-subdomain-layout.md` (verify strict compliance)

## Code Review Guidance

### Key Review Areas
- Pattern appropriateness for context complexity
- Domain layer purity (no I/O)
- Proper subdomain organization
- Shared types location
- Protocol placement (layered pattern only)

### Pattern Acceptance Note
Flat patterns are acceptable implementations:
- **Minimal-flat**: configuration, pipeline - check for entities/, services/
- **Organized-flat**: dataingestion - check for entities/, repositories/, services/
- **Layered**: assessment - check for domain/, application/, infrastructure/ separation

### Code Quality Checks
- Domain layer has no external deps
- Infrastructure layer has I/O
- Application layer coordinates (layered pattern)
- Subdomains are cohesive
- No cross-context imports

### ADR Compliance Verification
- [ ] Pattern appropriate for context complexity
- [ ] Domain layer is pure Python
- [ ] Subdomains organized by capability
- [ ] Protocols in domain/protocols/ (if layered pattern)
- [ ] Shared types in shared/

## Checklist
Before approving implementation, verify:
- [ ] Code matches approved plan
- [ ] ADR constraints are strictly followed
- [ ] Domain layer is pure
- [ ] Infrastructure has I/O
- [ ] Tests pass
- [ ] Code review comments are addressed

## Nested Subdomain Implementation Checks
- [ ] **shared/ purity**: Run `ls shared/protocols/*.py` — should contain only protocol definitions (Python Protocol classes, no concrete implementations)
- [ ] **adapters/ structure**: Run `ls adapters/*.py` — should contain only adapter implementations (concrete classes implementing shared protocols)
- [ ] **Subdomain structure**: Run `ls subdomains/*/` — each subdomain should have entities/, services/, value_objects/ directories
- [ ] **Per-domain ADRs**: Run `ls subdomains/*/adr-{adr-id}.md` — each subdomain should have its per-domain ADR file

For detailed Nested Subdomain enforcement commands, see `ddd-s-003-subdomain-deepening.md` phases and `packages/cleanmast/.agents/skills/adr-guardrails-skill/review-implementation.md`
