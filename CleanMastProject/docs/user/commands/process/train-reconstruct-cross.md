# process train-reconstruct-cross

## 概述

训练跨测风塔重构模型，分析多个测风塔之间的相关性，为数据缺失的测风塔建立基于其他测风塔的重构模型。

## 语法

```bash
julia bin/CleanMast.jl process train-reconstruct-cross <配置文件路径>
```

## 前置条件

- 必须先完成 `process reconstruct-single` 步骤
- 存在 `train-reconstruct-cross.toml` 配置文件
- 项目中有多个测风塔的重构数据（至少2个）

## 配置文件格式 (TOML)

### 基本结构

```toml
[[masts]]
name = "测风塔名称"
    [masts.input]
    sensors = "输入传感器配置文件"
    data = "输入数据文件"

[train]
output_dir = "输出目录"
min_overlap_days = 90.0
min_correlation = 0.7
max_std_deviation = 12.5
max_abs_offset = 45.0
min_data_points = 200
exclude_nan_results = true
```

### 配置参数

#### 测风塔配置 (`masts`)
- **name**: 测风塔唯一标识符
- **input.sensors**: 输入传感器元数据文件 (来自 reconstruct-single)
- **input.data**: 输入时间序列数据文件 (来自 reconstruct-single)

#### 训练设置 (`train`)
- **output_dir**: 训练结果输出目录
- **min_overlap_days**: 最小重叠天数，确保足够的训练数据（默认90天）
- **min_correlation**: 风速相关性最小阈值（默认0.7）
- **max_std_deviation**: 风向偏差最大标准偏差（默认12.5°）
- **max_abs_offset**: 风向偏移最大绝对值（默认45.0°）
- **min_data_points**: 统计显著性最小数据点数（默认200点）
- **exclude_nan_results**: 过滤NaN/Inf结果（默认true）

### 完整配置示例

```toml
[[masts]]
name = "测风塔-001"
    [masts.input]
    sensors = "./reconstruct-single/测风塔-001.sensors.yaml"
    data = "./reconstruct-single/测风塔-001.csv"

[[masts]]
name = "测风塔-002"
    [masts.input]
    sensors = "./reconstruct-single/测风塔-002.sensors.yaml"
    data = "./reconstruct-single/测风塔-002.csv"

[[masts]]
name = "测风塔-003"
    [masts.input]
    sensors = "./reconstruct-single/测风塔-003.sensors.yaml"
    data = "./reconstruct-single/测风塔-003.csv"

[train]
output_dir = "./train-reconstruct-cross"
min_overlap_days = 90.0
min_correlation = 0.7
max_std_deviation = 12.5
max_abs_offset = 45.0
min_data_points = 200
exclude_nan_results = true
```

## 输入文件

- **测风塔数据**: 来自 reconstruct-single 步骤的传感器配置和时间序列数据

## 输出文件

```
train-reconstruct-cross/
├── cross-mast-models/
│   ├── <目标测风塔>/
│   │   ├── <源测风塔>/
│   │   │   ├── windspeed_model.jld2     # 风速模型
│   │   │   ├── winddirection_model.jld2  # 风向模型
│   │   │   └── model_stats.yaml         # 模型统计
├── train-results.toml                   # 训练结果汇总
├── correlation-matrix.csv               # 相关性矩阵
└── training-report.yaml                 # 详细训练报告
```

### 训练结果汇总

`train-results.toml` 包含所有测风塔对的训练结果：

```toml
# 训练元数据
[metadata]
training_date = "2025-01-15T10:30:00.000Z"
total_mast_pairs = 6
qualified_pairs = 4

# 测风塔对训练结果
[[correlations]]
target_mast = "测风塔-001"
source_mast = "测风塔-002"
speed_correlation = 0.8523
direction_std = 18.45
data_coverage_days = 152.3
model_quality = "high"
```

## 配置生成

使用 `recommend` 命令生成配置文件：

```bash
julia bin/CleanMast.jl recommend train-reconstruct-cross projects/my-windfarm
```

## 下一步操作

跨塔模型训练完成后，可以执行：

1. **检查训练结果**: 查看 `train-results.toml` 中的模型性能
2. **生成重构配置**: `julia bin/CleanMast.jl recommend reconstruct-cross projects/my-windfarm`
3. **执行跨塔重构**: `julia bin/CleanMast.jl process reconstruct-cross projects/my-windfarm/reconstruct-cross.toml`