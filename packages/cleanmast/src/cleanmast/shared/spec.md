## Purpose
Root kernel for truly cross-cutting foundations

## Rules
- Bar for entry: used by 2+ contexts
- Timeseries types, path utils, atmospheric constants only
- No domain logic
- No context-specific types

## Anti-patterns
- Putting assessment-specific types here
- Putting IO here

## When in doubt
if only one context uses it, it belongs in that context's model/

## 业务说明 (Business description)

### Domain context

shared/ 提供跨 bounded context 共享的类型契约。所有领域代码通过这些类型通信。
入口标准: 必须被 2 个以上 context 使用。

### Key concepts

- **TimeSeriesData**: polars DataFrame + SensorColumn 列表 — 管道通用数据格式。
- **SensorColumn**: 传感器元数据 (类型/高度/朝向/统计方式/单位) — 不解析原始列名字符串。
- **TimeSeriesSource**: 数据 + 元数据文件路径对，指向 parquet 和 YAML 文件。
- **TimeRange**: 分析的起止时间窗口。
- 两种主要测量类型: `WindSpeed` (风速, m/s) 和 `WindDirection` (风向, deg)。

### Business constraints

- 传感器有物理属性: 安装高度 (m)、朝向 (N/S/E/W 代表不同支臂)、
  统计类型 (avg/std/max/min)。这些属性决定数据如何被处理和解释。
- 时序对齐是所有下游处理的前提 — 不同传感器的数据必须在时间轴上对齐。
