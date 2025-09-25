# reconstruct-cross.toml 配置文件

## 概述

`reconstruct-cross.toml` 定义跨测风塔重构配置。使用训练好的跨塔模型，利用其他测风塔的数据填补目标测风塔的数据缺失。

## 基本结构

```toml
# 训练元数据信息
[training_metadata]
qualified_speed_pairs = 合格风速模型对数
qualified_direction_pairs = 合格风向模型对数
total_mast_pairs = 总测风塔对数
train_results_file = "训练结果文件路径"
training_date = "训练日期"

# 测风塔配置
[[masts]]
name = "测风塔名称"

[masts.input]
data = "输入数据文件路径"
sensors = "输入传感器配置路径"

[masts.output]
data = "输出数据文件路径"
sensors = "输出传感器配置路径"

# 重构设置
[settings]
output_dir = "输出目录"
preserve_existing = 是否保持现有数据
min_confidence = 最小置信度
max_direction_uncertainty = 最大风向不确定性
generate_reports = 是否生成报告
backup_originals = 是否备份原文件

# 重构优先级配置
[[reconstruction_priorities]]
priority_level = 优先级级别
min_correlation = 最小相关系数
max_direction_std = 最大风向标准差

[[reconstruction_priorities.jobs]]
target_mast = "目标测风塔"
source_mast = "源测风塔"
model_dir = "模型目录"
priority = 优先级
speed_correlation = 风速相关系数
direction_std = 风向标准差
data_coverage_days = 数据覆盖天数
variables = ["重构变量列表"]
```

## 配置参数

### 训练元数据 ([training_metadata])

记录训练过程的相关信息：

```toml
[training_metadata]
qualified_speed_pairs = 6
qualified_direction_pairs = 6
total_mast_pairs = 6
train_results_file = "train-reconstruct-cross/train-results.toml"
training_date = "2025-09-24T14:40:05.475"
```

### 测风塔配置 ([[masts]])

#### 必需参数

**name** (字符串)
- 测风塔标识符

```toml
name = "pn-002824"
```

**input** (表格)
- 输入数据文件和传感器配置文件
- 通常来自 `reconstruct-single/` 目录

```toml
[masts.input]
data = "./reconstruct-single/pn-002824.csv"
sensors = "./reconstruct-single/pn-002824.sensors.yaml"
```

**output** (表格)
- 跨塔重构后数据的输出路径
- 通常输出到 `reconstruct-cross/` 目录

```toml
[masts.output]
data = "./reconstruct-cross/pn-002824_reconstructed.csv"
sensors = "./reconstruct-cross/pn-002824_reconstructed.sensors.yaml"
```

### 重构设置 ([settings])

#### 可选参数

**output_dir** (字符串)
- 重构输出目录
- 默认值："./reconstruct-cross"

```toml
output_dir = "./reconstruct-cross"
```

**preserve_existing** (布尔值)
- 是否只填补缺失数据，不覆盖现有值
- 默认值：true

```toml
preserve_existing = true
```

**min_confidence** (浮点数)
- 尝试重构的最小相关性
- 默认值：0.7

```toml
min_confidence = 0.7
```

**max_direction_uncertainty** (浮点数)
- 最大风向标准差（度）
- 默认值：45.0

```toml
max_direction_uncertainty = 45.0
```

**generate_reports** (布尔值)
- 是否生成重构质量报告
- 默认值：true

```toml
generate_reports = true
```

**backup_originals** (布尔值)
- 重构前是否创建原文件备份
- 默认值：true

```toml
backup_originals = true
```

### 重构优先级 ([[reconstruction_priorities]])

定义重构作业的执行顺序和质量标准：

```toml
[[reconstruction_priorities]]
priority_level = 1
min_correlation = 0.7
max_direction_std = 15.0

[[reconstruction_priorities.jobs]]
target_mast = "pn-013945"
source_mast = "pn-002824"
model_dir = "train-reconstruct-cross/cross-mast-models/pn-013945/pn-002824"
priority = 1
speed_correlation = 0.8895
direction_std = 24.54
data_coverage_days = 396.88
variables = ["windspeed", "winddirection"]
```

## 重构优先级机制

系统按以下顺序执行重构：
1. **Priority Level**: 优先级级别越低，执行越早
2. **Job Priority**: 同级别内，优先级数值越小，执行越早
3. **Variables**: 根据相关性质量决定重构哪些变量
   - `["windspeed", "winddirection"]`: 重构风速和风向
   - `["windspeed"]`: 仅重构风速

## 配置生成

此配置文件通常由 `train-reconstruct-cross` 命令自动生成：

```bash
# 先训练跨塔模型
julia bin/CleanMast.jl process train-reconstruct-cross projects/my-windfarm

# 然后生成重构配置
julia bin/CleanMast.jl recommend reconstruct-cross projects/my-windfarm
```

## 执行重构

```bash
# 执行跨塔重构
julia bin/CleanMast.jl process reconstruct-cross projects/my-windfarm
```