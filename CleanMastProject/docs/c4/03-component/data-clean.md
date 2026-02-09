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

## 配置接口

使用 `process-clean.toml` 定义清洗规则和测风塔处理配置。

## 数据清洗规则详解

基于代码实现 (`src/DataClean/Rules/*.jl`)，系统支持以下四种清洗规则类型：

### 1. 范围检测 (Range)

**实现文件**: `ProcessRange.jl`

检测传感器数值是否超出物理合理范围。

**配置示例**:
```toml
[[rules]]
name = "风速范围检查"
sensor_type = "WindSpeed"
stat_type = "avg"
criteria_type = "Range"
min = 0.0
max = 50.0
```

**检测逻辑**:
- 值 < min → 违规
- 值 > max → 违规
- 缺失值(ismissing) → 忽略

**典型阈值** (参考 `process-clean.toml` 实际配置):
- 风速: 0-50 m/s
- 风向: 0-360°
- 温度: -40°C to +50°C

---

### 2. 结冰检测 (Icing)

**实现文件**: `ProcessIcing.jl`

检测传感器结冰导致的测量停滞。

**配置示例**:
```toml
[[rules]]
name = "风速结冰检测"
sensor_type = "WindSpeed"
height = 80.0
criteria_type = "Icing"
time_range = 7200      # 2小时 = 7200秒
max_change = 0.02      # 最大变化量
```

**检测逻辑**:
1. 滑动窗口检查 (默认 7200秒 = 2小时)
2. 如果窗口内数值变化 < max_change → 标记为结冰
3. 窗口内所有时间点都标记为违规

**关键参数**:
- `time_range`: 检测窗口时长（秒），默认 7200
- `max_change`: 最大允许变化量，默认 0.02

---

### 3. 层差检测 (Layer Difference)

**实现文件**: `ProcessLayerDiff.jl`

检测不同高度层间的异常差异。

**配置示例**:
```toml
[[rules]]
name = "风向层差检查"
sensor_type = "WindDirection"
lower_layer_height = 20.0
criteria_type = "LayerDifference"

[rules.criteria.abs_diff]
min = 0.0
max = 30.0              # 最大允许风向差 30°

[rules.criteria.lower_wind_speed]
min = 3.0               # 下层风速需 ≥3 m/s 才检测
max = 25.0
```

**检测逻辑**:
1. 查找下层传感器（高度差 ≤ lower_layer_height）
2. 计算两层间差值：
   - 风速: 绝对差值
   - 风向: 环形差值（处理 350° vs 10° 情况）
3. 如果差值超出范围 → 标记违规
4. 可选：检查下层风速是否在指定范围内

**特殊处理**:
- 自动查找最近的风速传感器（10m范围内）用于风速条件检查
- 风向使用环形差值计算（`abs_degree_diff`）

---

### 4. 可用性检测 (Availability)

**实现文件**: `ProcessAvailability.jl`

根据可用性传感器标记低质量数据。

**配置示例**:
```toml
[[rules]]
name = "数据可用性检查"
sensor_type = "Availability"
height = 80.0
criteria_type = "Availability"
low_threshold = 90.0    # 可用性低于90%时标记
```

**检测逻辑**:
1. 查找指定高度的 Availability 传感器
2. 当可用性值 < low_threshold 或缺失时：
   - 标记该高度**所有**传感器为违规
3. 高度匹配为精确匹配

---

## 配置接口

使用 `process-clean.toml` 定义清洗规则和测风塔处理配置。

## 注意事项

- 规则支持范围检测、层差检测、结冰检测和可用性检测四种类型
- 违规数据将被标记为缺失值（`ismissing`）
- 支持按测风塔分别配置输入输出路径
- 所有规则并行执行，结果合并
