## Purpose
Root kernel for truly cross-cutting foundations

## Rules
- Bar for entry: used by 2+ contexts.
- Only cross-context contract types and constants belong here — timeseries
  data/metadata types and the config IR models consumed by multiple contexts
  (both live under `timeseries/`).

## Anti-patterns
- Putting assessment-specific types here
- Putting IO here

## When in doubt
- Apply the 2+ contexts bar (Rules); otherwise the type belongs in the
  consuming context's `model/`.

## 业务说明 (Business description)

### Domain context

shared/ 提供跨 bounded context 共享的类型契约。所有领域代码通过这些类型通信。

### Key concepts

Timeseries 契约类型 (TimeSeriesData, SensorColumn, TimeSeriesSource, TimeRange)
的定义见 `shared/timeseries/spec.md`。

- 两种主要测量类型: `WindSpeed` (风速, m/s) 和 `WindDirection` (风向, deg)。

### Business constraints

- 传感器有物理属性: 安装高度 (m)、朝向 (N/S/E/W 代表不同支臂)、
  统计类型 (avg/std/max/min)。这些属性决定数据如何被处理和解释。
- 时序对齐是所有下游处理的前提 — 不同传感器的数据必须在时间轴上对齐。
