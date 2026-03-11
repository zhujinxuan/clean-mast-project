# Phase: Review-Implementation - Context Maps

## When to Use
Load this file when reviewing code implementation for context relationships.

## Related ADR
- Main ADR: `adr/ddd-s-002-context-maps.md` (verify strict compliance)

## Code Review Guidance

### Key Review Areas
- Protocol definition in shared/
- Dependency inversion (depend on protocol)
- No direct context-to-context imports
- Bootstrap properly wires dependencies

### Code Quality Checks
- Protocols are in shared/protocols/
- Implementations are in infrastructure/
- Domain layer is protocol-agnostic
- No circular imports

### ADR Compliance Verification
- [ ] Repository protocol defined
- [ ] No direct context imports
- [ ] Dependency injection used
- [ ] Protocol/implementation separation
- [ ] Integration via abstractions

## Checklist
Before approving implementation, verify:
- [ ] Code matches approved plan
- [ ] ADR constraints are strictly followed
- [ ] Protocols properly defined
- [ ] Dependencies injected
- [ ] Tests use mocks
- [ ] Code review comments are addressed
