# DataClean 组件

## 概述

DataClean 组件负责应用可配置的数据清洗规则到时间序列数据，检测并标记数据质量问题。

## 职责

- 应用传感器数值范围验证规则
- 检测高度间层差异常
- 识别结冰条件期间的测量数据
- 检查数据可用性并标记低质量时段
- 记录所有违规事件并生成报告

## 输入

| 输入 | 类型 | 来源 |
|------|------|------|
| 时间序列数据 | TimeSeriesData | ParseSensors |
| 清洗规则配置 | TOML | 用户配置 |
| 测风塔配置 | TOML | 用户配置 |

## 输出

| 输出 | 类型 | 去向 |
|------|------|------|
| 清洗后的数据 | TimeSeriesData | TowerShading, ReconstructSingleMast |
| 违规摘要报告 | YAML | Reports |

## 依赖关系

- **上游**: ParseSensors
- **下游**: TowerShading, ReconstructSingleMast

## 支持的清洗规则类型

基于 IEC 61400-12-1 数据质量要求实现。规则实现位于 `src/DataClean/Rules/` 目录。

### 1. 范围检测 (Range)

**实现参考**: `src/DataClean/Rules/ProcessRange.jl`

检测传感器数值是否超出物理合理范围。所有阈值均在 `process-clean.toml` 中配置，包括各传感器类型的最小值和最大值限制。

### 2. 结冰检测 (Icing)

**实现参考**: `src/DataClean/Rules/ProcessIcing.jl`

检测传感器结冰导致的测量停滞现象。检测窗口时长和最大允许变化量等参数均在 `process-clean.toml` 中配置。

### 3. 层差检测 (Layer Difference)

**实现参考**: `src/DataClean/Rules/ProcessLayerDiff.jl`

检测不同高度层间的异常差异，包括风速绝对差值和风向环形差值。高度阈值和差值范围在 `process-clean.toml` 中配置。

### 4. 可用性检测 (Availability)

**实现参考**: `src/DataClean/Rules/ProcessAvailability.jl`

根据可用性传感器标记低质量数据。低阈值参数在 `process-clean.toml` 中配置。

## 配置接口

使用 `process-clean.toml` 定义清洗规则和测风塔处理配置。

## 注意事项

- 规则支持范围检测、层差检测、结冰检测和可用性检测四种类型
- 违规数据将被标记为缺失值（`ismissing`）
- 支持按测风塔分别配置输入输出路径
- 所有规则并行执行，结果合并
