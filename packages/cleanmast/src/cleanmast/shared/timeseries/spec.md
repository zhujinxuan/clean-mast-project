## Purpose
Foundational time-series types and loaders

## Rules
- TimeSeriesData, TimeSeriesSource, SensorColumn defined here
- Parquet loader as infrastructure
- TimeSeriesData migrated to this package ✓; SensorColumn/TimeSeriesSource re-exported from dataingestion (stable)

## Anti-patterns
- Context-specific types in shared
- Domain logic in loaders

## When in doubt
Ask whether the consumer is generic infrastructure or a specific bounded context
