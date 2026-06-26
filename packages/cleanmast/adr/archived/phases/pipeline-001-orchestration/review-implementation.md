# Phase: Review-Implementation - Pipeline Orchestration

## When to Use
Load this file when reviewing code implementation for pipeline.

## Related ADR
- Main ADR: `adr/pipeline-001-orchestration.md` (verify strict compliance)

## Code Review Guidance

### Key Review Areas
- Phase protocol compliance
- PipelineContext orchestration
- Julia integration via files
- Error handling per phase

### Code Quality Checks
- Each phase implements PipelinePhase
- Input/output types match contracts
- No direct phase-to-phase calls
- Julia subprocess properly handles errors

### ADR Compliance Verification
- [ ] 5 phases implemented
- [ ] PipelinePhase protocol used
- [ ] PipelineContext orchestrates
- [ ] Julia via files only
- [ ] Error handling per phase

## Checklist
Before approving implementation, verify:
- [ ] Code matches approved plan
- [ ] ADR constraints are strictly followed
- [ ] All phases properly connected
- [ ] Julia integration works
- [ ] Tests pass
- [ ] Code review comments are addressed
