## Purpose
Foundational time-series types, I/O, and loaders.

## Rules
- ``TimeSeriesData``, ``SensorColumn``, ``TimeSeriesSource``, ``TimeRange`` defined
  in the top-level ``cleanmast.shared.timeseries`` module.
- ``io/`` subpackage provides the repository protocol
  (``TimeSeriesRepository``), the file-backed implementation
  (``FileTimeSeriesRepository``), and validation / schema helpers
  (``create_wind_schema``, ``validate_timeseries``). Its
  ``load_timeseries`` / ``save_timeseries`` families are the canonical
  entry points for reading/writing timeseries data.
- ``io/`` is also the sole gateway for TOML sensor-metadata I/O
  (``tomli`` / ``tomli_w``) — configuration services route through
  ``FileTimeSeriesRepository``, not raw TOML.

## Anti-patterns
- Context-specific types in shared
- Domain logic in loaders

## When in doubt
Ask whether the consumer is generic infrastructure or a specific bounded context
