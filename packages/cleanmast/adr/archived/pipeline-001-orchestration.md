---
id: pipeline-001-orchestration
name: orchestration
description: Pipeline workflow orchestration with phase management
tags: [pipeline, workflow, orchestration, cleanmast]
applies_when:
  - implementing pipeline phases
  - orchestrating workflow
  - Julia integration
---

# PIPELINE-001: Orchestration

## Constraint (MUST)
2. **PipelinePhase interface** - every phase implements input/output contracts
3. **Phase order**: Configuration → DataIngestion → DataProcessing → Analysis → Reporting
4. **File-based Julia integration** - Parquet in/out, never direct memory
5. **Phase outputs become inputs** - explicit data flow
6. **Error handling per phase** - continue or abort based on config

## Rationale (WHY)

Explicit phases make data flow visible. PipelineContext coordinates without coupling. File-based Julia integration is recoverable. Phase contracts prevent mismatched inputs.

## Anti-Pattern (AVOID)

```python
# ❌ Phases calling each other directly
class DataIngestionPhase:
    def execute(self):
        cleaner = DataProcessingPhase()  # NEVER
        return cleaner.clean(data)
jl.eval(f"process({data.ptr})")  # NEVER - use files
phase1.output.some_internal_field  # NEVER - use explicit contracts
```

## Phase Links
| Phase | File |
|-------|------|
| Plan | [on-plan.md](./phases/pipeline-001-orchestration/on-plan.md) |
| Review Plan | [review-plan.md](./phases/pipeline-001-orchestration/review-plan.md) |
| Code | [code.md](./phases/pipeline-001-orchestration/code.md) |
| Review | [review-implementation.md](./phases/pipeline-001-orchestration/review-implementation.md) |
## References
- `ddd-s-002-context-maps.md` - Context orchestration
- `persistence-001-parquet-storage.md` - Parquet for Julia integration
