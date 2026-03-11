# Phase: On-Plan - Pipeline Orchestration

## When to Use
Load this file during the planning/design phase when designing pipeline workflow.

## Related ADR
- Main ADR: `adr/pipeline-001-orchestration.md` (load first for constraints)

## Design Guidance

### Pipeline Phase Flow

```
ConfigurationPhase
    ↓ Config
DataIngestionPhase
    ↓ TimeSeriesData
DataProcessingPhase
    ↓ CleanedData
AnalysisPhase
    ↓ AnalysisResult
ReportingPhase
    ↓ Report
```

### Phase Interface Design

```python
class PipelinePhase(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def input_type(self) -> type: ...
    @property
    def output_type(self) -> type: ...
    def execute(self, input_data: Any) -> Any: ...
```

### Key Considerations
- Each phase has explicit input/output types
- PipelineContext orchestrates, phases execute
- Error handling per phase (continue or abort)
- File-based Julia integration for AnalysisPhase

### Phase Responsibilities
1. **ConfigurationPhase**: Parse config, validate inputs
2. **DataIngestionPhase**: Load raw data, create TimeSeriesData
3. **DataProcessingPhase**: Clean, reconstruct, transform
4. **AnalysisPhase**: Calculate statistics (Julia integration)
5. **ReportingPhase**: Generate output files/reports

### Common Pitfalls
- Phases calling each other directly
- Direct Julia memory sharing
- Hidden dependencies between phases
- PipelineContext knowing phase internals

## Checklist
Before proceeding to implementation, verify:
- [ ] 5 pipeline phases defined
- [ ] Input/output contracts specified
- [ ] Error handling strategy planned
- [ ] Julia integration approach defined
- [ ] ADR constraints are respected
