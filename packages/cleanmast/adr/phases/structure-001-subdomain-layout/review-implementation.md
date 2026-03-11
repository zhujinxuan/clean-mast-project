# Phase: Review-Implementation - Subdomain Layout

## When to Use
Load this file when reviewing code implementation for folder structure.

## Related ADR
- Main ADR: `adr/structure-001-subdomain-layout.md` (verify strict compliance)

## Code Review Guidance

### Key Review Areas
- 3-layer architecture compliance
- Domain layer purity (no I/O)
- Proper subdomain organization
- Shared types location
- Protocol placement

### Code Quality Checks
- Domain layer has no external deps
- Infrastructure layer has I/O
- Application layer coordinates
- Subdomains are cohesive
- No cross-context imports

### ADR Compliance Verification
- [ ] 3-layer architecture respected
- [ ] Domain layer is pure Python
- [ ] Subdomains organized by capability
- [ ] Protocols in domain/protocols/
- [ ] Shared types in shared/

## Checklist
Before approving implementation, verify:
- [ ] Code matches approved plan
- [ ] ADR constraints are strictly followed
- [ ] Domain layer is pure
- [ ] Infrastructure has I/O
- [ ] Tests pass
- [ ] Code review comments are addressed
