# Phase: Code - Pipeline Orchestration

## When to Use
Load this file during the implementation phase when implementing pipeline.

## Related ADR
- Main ADR: `adr/pipeline-001-orchestration.md` (follow constraints strictly)

## Implementation Guidance

### Key Implementation Steps
1. Define `PipelinePhase` protocol in shared/protocols/
2. Create 5 phase implementations in contexts/
3. Implement `PipelineContext` as orchestrator
4. Add error handling per phase
5. Implement Julia integration via subprocess

### PipelineContext Implementation

```python
from typing import Any, list
from shared.protocols import PipelinePhase

class PipelineContext:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.phases: list[PipelinePhase] = [
            ConfigurationPhase(config),
            DataIngestionPhase(),
            DataProcessingPhase(),
            AnalysisPhase(),
            ReportingPhase(),
        ]
    
    def run(self, initial_input: Any) -> Any:
        data = initial_input
        for phase in self.phases:
            try:
                data = phase.execute(data)
            except PhaseError as e:
                if self.config.continue_on_error:
                    self.log_warning(f"Phase {phase.name} failed: {e}")
                    continue
                raise
        return data
```

### Julia Integration Phase

```python
import subprocess
from pathlib import Path
from shared.types import TimeSeriesData

class JuliaAnalysisPhase:
    def __init__(self, repository: TimeSeriesRepository):
        self.repository = repository
    
    def execute(self, input_data: TimeSeriesData) -> AnalysisResult:
        input_path = Path("/tmp/analysis_input.parquet")
        output_path = Path("/tmp/analysis_output.parquet")
        
        # Save input
        self.repository.save(input_data, input_path)
        
        # Call Julia
        subprocess.run([
            "julia", "-e",
            f"using CleanMast; process_parquet('{input_path}', '{output_path}')"
        ], check=True)
        
        # Load output
        return self.repository.load(output_path)
```

## Checklist
Before marking implementation complete, verify:
- [ ] PipelinePhase protocol defined
- [ ] All 5 phases implemented
- [ ] PipelineContext orchestrates
- [ ] Error handling works
- [ ] Julia integration via files
- [ ] Tests cover all phases
