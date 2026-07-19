## Purpose
Foundational time-series types and loaders

## Rules
- TimeSeriesData, SensorColumn, TimeSeriesSource, TimeRange defined here
- Parquet loader as infrastructure

## Anti-patterns
- Context-specific types in shared
- Domain logic in loaders

## When in doubt
Ask whether the consumer is generic infrastructure or a specific bounded context
