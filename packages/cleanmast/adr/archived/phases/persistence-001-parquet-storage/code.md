# Phase: Code - Parquet Storage

## When to Use
Load this file during the implementation phase when implementing persistence.

## Related ADR
- Main ADR: `adr/persistence-001-parquet-storage.md` (follow constraints strictly)

## Implementation Guidance

### Key Implementation Steps
1. Define `TimeSeriesRepository` protocol in shared/protocols/
2. Create `ParquetTimeSeriesRepository` in infrastructure/
3. Implement metadata serialization/deserialization
4. Add tests with sample parquet files
5. Handle edge cases (missing metadata, schema changes)

### Repository Implementation

```python
import json
import polars as pl
from pathlib import Path
from shared.types import TimeSeriesData

class ParquetTimeSeriesRepository:
    def load(self, path: Path) -> TimeSeriesData:
        df = pl.read_parquet(path)
        # Read metadata from parquet
        metadata = json.loads(df.schema.get("sensor_metadata", "{}"))
        return TimeSeriesData(
            df=df,
            sensors=metadata.get("sensors", [])
        )
    
    def save(self, data: TimeSeriesData, path: Path) -> None:
        metadata = {
            "cleanmast_sensors": json.dumps({
                "sensors": [s.model_dump(by_alias=True) for s in data.sensors]
            })
        }
        data.df.write_parquet(path, metadata=metadata)
```

### Testing Strategy
- Unit tests with temporary files
- Mock repository for domain tests
- Integration tests with real parquet
- Metadata round-trip verification

## Checklist
Before marking implementation complete, verify:
- [ ] Repository protocol defined
- [ ] Parquet implementation works
- [ ] Metadata embedded correctly
- [ ] Tests cover edge cases
- [ ] No polars in domain layer
- [ ] Julia integration possible
