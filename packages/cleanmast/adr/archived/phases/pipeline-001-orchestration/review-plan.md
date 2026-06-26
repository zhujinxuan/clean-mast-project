# Phase: Review-Plan - Pipeline Orchestration

## When to Use
Load this file when reviewing a design/plan for pipeline workflow.

## Related ADR
- Main ADR: `adr/pipeline-001-orchestration.md` (verify compliance)

## Review Guidance

### Key Review Points
1. **5 phases defined**: Config, Ingestion, Processing, Analysis, Reporting
2. **PipelinePhase interface**: All phases implement protocol
3. **Explicit contracts**: Input/output types defined
4. **File-based Julia**: Parquet in/out, not memory
5. **Error handling**: Per-phase continue/abort logic

### Red Flags
- Phases with direct dependencies
- Missing input/output contracts
- Memory-based Julia integration
- PipelineContext too tightly coupled

### Approval Criteria
- Phase chain is linear (no branches)
- Each phase has clear contract
- Julia integration via files
- Error handling strategy defined

## Checklist
Before approving the plan, verify:
- [ ] Design aligns with ADR constraints
- [ ] All 5 phases defined
- [ ] Input/output contracts specified
- [ ] Julia integration via files
- [ ] Error handling planned
- [ ] Review comments are resolved
