# process reconstruct-cross

## 概述

使用训练好的跨测风塔模型进行数据重构，通过其他测风塔的数据填补目标测风塔的缺失数据。

## 语法

```bash
julia bin/CleanMast.jl process reconstruct-cross <配置文件路径>
```

## 前置条件

- 必须先完成 `process train-reconstruct-cross` 步骤
- 存在 `reconstruct-cross.toml` 配置文件
- 有可用的跨塔训练模型文件

## 配置文件格式 (TOML)

### 基本结构

```toml
[training_metadata]
# 训练元数据信息

[[masts]]
name = "测风塔名称"
    [masts.input]
    sensors = "输入传感器配置文件"
    data = "输入数据文件"
    [masts.output]
    sensors = "输出传感器配置文件"
    data = "输出数据文件"

[settings]
output_dir = "输出目录"
min_confidence = 0.7
max_direction_uncertainty = 12.5
preserve_existing = true
generate_reports = true
backup_originals = true

[[reconstruction_priorities]]
priority_level = 1
min_correlation = 0.7
max_direction_std = 15.0
    [[reconstruction_priorities.jobs]]
    target_mast = "目标测风塔"
    source_mast = "源测风塔"
    model_dir = "模型目录路径"
    priority = 1
    speed_correlation = 0.85
    direction_std = 12.3
    data_coverage_days = 180.5
    variables = ["windspeed", "winddirection"]
```

### 配置参数

#### 训练元数据 (`training_metadata`)
- 包含来自训练阶段的元数据信息
- 自动从训练结果生成，通常不需要手动编辑

#### 测风塔配置 (`masts`)
- **name**: 测风塔唯一标识符
- **input.sensors**: 输入传感器元数据文件 (来自 reconstruct-single)
- **input.data**: 输入时间序列数据文件 (来自 reconstruct-single)
- **output.sensors**: 输出传感器元数据文件
- **output.data**: 输出时间序列数据文件

#### 重构设置 (`settings`)
- **output_dir**: 重构结果输出目录
- **min_confidence**: 最小置信度阈值（默认0.7）
- **max_direction_uncertainty**: 风向不确定度最大值（默认45.0°）
- **preserve_existing**: 仅填补缺失数据，不覆盖现有值（默认true）
- **generate_reports**: 生成重构质量报告（默认true）
- **backup_originals**: 备份原始文件（默认true）

#### 重构优先级 (`reconstruction_priorities`)
- **priority_level**: 优先级等级（1=最高，2=中等，等等）
- **min_correlation**: 该优先级的最小相关系数
- **max_direction_std**: 该优先级的最大风向标准偏差
- **jobs**: 该优先级的重构任务列表

#### 重构任务 (`jobs`)
- **target_mast**: 目标测风塔名称（要重构的塔）
- **source_mast**: 源测风塔名称（提供数据的塔）
- **model_dir**: 训练好的模型文件目录路径
- **priority**: 任务优先级
- **speed_correlation**: 风速相关系数
- **direction_std**: 风向标准偏差
- **data_coverage_days**: 训练数据覆盖天数
- **variables**: 要重构的变量列表（如 `["windspeed", "winddirection"]`）

### 完整配置示例

```toml
[training_metadata]
qualified_direction_pairs = 2
total_mast_pairs = 6
qualified_speed_pairs = 6
training_date = "2025-01-15T10:30:00.000Z"

[[masts]]
name = "测风塔-001"
    [masts.input]
    sensors = "./reconstruct-single/测风塔-001.sensors.yaml"
    data = "./reconstruct-single/测风塔-001.csv"
    [masts.output]
    sensors = "./reconstruct-cross/测风塔-001_reconstructed.sensors.yaml"
    data = "./reconstruct-cross/测风塔-001_reconstructed.csv"

[[masts]]
name = "测风塔-002"
    [masts.input]
    sensors = "./reconstruct-single/测风塔-002.sensors.yaml"
    data = "./reconstruct-single/测风塔-002.csv"
    [masts.output]
    sensors = "./reconstruct-cross/测风塔-002_reconstructed.sensors.yaml"
    data = "./reconstruct-cross/测风塔-002_reconstructed.csv"

[settings]
output_dir = "./reconstruct-cross"
min_confidence = 0.7
max_direction_uncertainty = 15.0
preserve_existing = true
generate_reports = true
backup_originals = true

[[reconstruction_priorities]]
priority_level = 1
min_correlation = 0.8
max_direction_std = 12.0
    [[reconstruction_priorities.jobs]]
    target_mast = "测风塔-001"
    source_mast = "测风塔-002"
    model_dir = "train-reconstruct-cross/cross-mast-models/测风塔-001/测风塔-002"
    priority = 1
    speed_correlation = 0.85
    direction_std = 10.2
    data_coverage_days = 185.3
    variables = ["windspeed", "winddirection"]
```

## 输入文件

- **测风塔数据**: 来自 reconstruct-single 步骤的传感器配置和时间序列数据
- **训练模型**: 来自 train-reconstruct-cross 步骤的 `.jld2` 模型文件

## 输出文件

- `reconstruct-cross/<测风塔名称>_reconstructed.csv`: 跨塔重构后的完整数据
- `reconstruct-cross/<测风塔名称>_reconstructed.sensors.yaml`: 更新的传感器元数据
- `reconstruct-cross/reconstruction-report.yaml`: 详细的重构报告
- `reconstruct-cross/quality-metrics.csv`: 重构质量指标

## 配置生成

使用 `recommend` 命令生成配置文件：

```bash
julia bin/CleanMast.jl recommend reconstruct-cross projects/my-windfarm
```

**注意**: 此配置文件通常从 `train-reconstruct-cross` 的训练结果自动生成。

## 下一步操作

跨塔重构完成后，可以执行：

1. **质量评估**: 检查重构报告和质量指标
2. **数据分析**: `julia bin/CleanMast.jl analyze reconstruct-cross projects/my-windfarm`
3. **继续处理**: 进入中尺度训练或代表年分析