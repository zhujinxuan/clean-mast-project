# Phase: Code - Context Maps

## When to Use
Load this file during the implementation phase when implementing context integrations.

## Related ADR
- Main ADR: `adr/ddd-s-002-context-maps.md` (follow constraints strictly)

## Implementation Guidance

### Key Implementation Steps
1. Define `TimeSeriesRepository` protocol in shared/protocols/
2. Implement protocol in DataIngestion infrastructure/
3. DataProcessing depends on protocol, not implementation
4. Configure dependency injection in bootstrap.py
5. PipelineContext wires everything together

### Protocol Example
```python
from typing import Protocol
from shared.types import TimeSeriesData
from pathlib import Path

class TimeSeriesRepository(Protocol):
    def load(self, path: Path) -> TimeSeriesData: ...
    def save(self, data: TimeSeriesData, path: Path) -> None: ...
```

### Integration Example
```python
# DataProcessing application layer
class DataCleaningUseCase:
    def __init__(self, repository: TimeSeriesRepository):
        self.repository = repository
    
    def execute(self, input_path: Path, output_path: Path):
        data = self.repository.load(input_path)
        cleaned = self.cleaner.clean(data)
        self.repository.save(cleaned, output_path)
```

## Checklist
Before marking implementation complete, verify:
- [ ] Protocol defined in shared/
- [ ] Implementation in infrastructure/
- [ ] Domain depends on protocol only
- [ ] Bootstrap wires dependencies
- [ ] Tests use mocks for protocol
- [ ] No direct context imports
