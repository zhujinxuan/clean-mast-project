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

## 业务说明 (Business description)

### Domain context

timeseries 是项目的核心数据层。所有测风塔传感器数据、重建数据、
补全数据均以 timeseries 格式流动。I/O 子包 (`io/`) 提供文件持久化
(apache parquet + YAML 元数据)。

### Key concepts

- **Parquet**: 列式存储格式，适合大规模时序数据的压缩和快速查询。
- **YAML 传感器元数据**: 与 parquet 数据文件成对存在，描述每个列对应的传感器。
- **TimeSeriesRepository**: 加载/保存 timeseries 的抽象接口；
  `FileTimeSeriesRepository` 是 parquet 文件系统实现。
- **数据验证**: `create_wind_schema` 和 `validate_timeseries` 确保
  数据格式和元数据在管道各阶段间一致。

### Business constraints

- 文件存储是 pipeline 的持久化层: 每个阶段的输出是下一阶段的输入。
- 传感器元数据必须与数据文件同步: 修改列名需同时更新 YAML 元数据。
