# recommend reconstruct-cross

## 概述

生成跨测风塔重构配置文件。基于训练好的跨塔模型，为数据缺失较多的测风塔配置重构参数和优先级策略。

## 语法

```bash
julia bin/CleanMast.jl recommend reconstruct-cross <项目目录>
```

## 实现位置

**核心实现**: `src/ReconstructCross/RecommendReconstructCrossCommand.jl`

## 前置条件

- 必须先完成 `process train-reconstruct-cross` 步骤
- 存在训练好的跨塔模型文件
- 有可用的训练结果统计信息

## 功能描述

### 1. 训练结果分析
- 读取 `train-reconstruct-cross/train-results.toml` 训练结果
- 分析所有测风塔对的模型性能指标
- 评估模型的适用性和可靠性

### 2. 重构优先级设定
- 根据相关系数和方向标准偏差设置优先级
- 高质量模型优先使用
- 建立多级降级策略

### 3. 自动配置生成
- 创建所有测风塔的输入输出配置
- 设置重构参数和质量控制标准
- 配置模型选择和应用策略

## 输出配置示例

基于 `projects/pn-3masts/reconstruct-cross.toml`:

```toml
# 训练元数据信息
[training_metadata]
qualified_direction_pairs = 0        # 合格的风向模型对数
total_mast_pairs = 6                # 总测风塔对数
train_results_file = "projects/pn-3masts/train-reconstruct-cross/train-results.toml"
qualified_speed_pairs = 6           # 合格的风速模型对数
training_date = "2025-09-20T01:10:04.636"

# 测风塔重构配置
[[masts]]
name = "pn-002824"
    [masts.input]
    data = "./reconstruct-single/pn-002824.csv"
    sensors = "./reconstruct-single/pn-002824.sensors.yaml"
    [masts.output]
    data = "./reconstruct-cross/pn-002824_reconstructed.csv"
    sensors = "./reconstruct-cross/pn-002824_reconstructed.sensors.yaml"

[[masts]]
name = "pn-013945"
    [masts.input]
    data = "./reconstruct-single/pn-013945.csv"
    sensors = "./reconstruct-single/pn-013945.sensors.yaml"
    [masts.output]
    data = "./reconstruct-cross/pn-013945_reconstructed.csv"
    sensors = "./reconstruct-cross/pn-013945_reconstructed.sensors.yaml"

# 重构设置
[settings]
min_confidence = 0.7                # 最小置信度
max_direction_uncertainty = 45.0    # 最大风向不确定度
backup_originals = true             # 备份原始数据
output_dir = "./reconstruct-cross"  # 输出目录
preserve_existing = true            # 保留现有数据
generate_reports = true             # 生成重构报告

# 重构优先级配置（优先级1 - 最高质量）
[[reconstruction_priorities]]
priority_level = 1
min_correlation = 0.7
max_direction_std = 15.0

    # 具体重构任务
    [[reconstruction_priorities.jobs]]
    model_dir = "train-reconstruct-cross/cross-mast-models/pn-013945/pn-002824"
    priority = 1
    variables = ["windspeed"]
    data_coverage_days = 396.88       # 数据覆盖天数
    target_mast = "pn-013945"         # 目标测风塔
    speed_correlation = 0.8895        # 风速相关系数
    source_mast = "pn-002824"         # 源测风塔
    direction_std = 24.54             # 风向标准偏差

# 重构优先级配置（优先级2 - 中等质量）
[[reconstruction_priorities]]
priority_level = 2
min_correlation = 0.5
max_direction_std = 20.0

    [[reconstruction_priorities.jobs]]
    model_dir = "train-reconstruct-cross/cross-mast-models/pn-013945/pn-014576"
    priority = 2
    variables = ["windspeed"]
    data_coverage_days = 295.83
    target_mast = "pn-013945"
    speed_correlation = 0.6989
    source_mast = "pn-014576"
    direction_std = 40.04
```

## 配置结构说明

### 训练元数据
- `qualified_speed_pairs`: 通过质量检验的风速模型对数
- `qualified_direction_pairs`: 通过质量检验的风向模型对数
- `train_results_file`: 训练结果文件路径
- `training_date`: 训练完成时间

### 重构设置
- `min_confidence`: 模型应用的最小置信度要求
- `max_direction_uncertainty`: 风向重构的最大不确定度
- `backup_originals`: 是否备份原始数据文件
- `preserve_existing`: 是否保留已存在的重构数据
- `generate_reports`: 是否生成详细的重构报告

### 优先级策略
- **priority_level**: 优先级等级（1最高，数字越大优先级越低）
- **min_correlation**: 该优先级下的最小相关系数要求
- **max_direction_std**: 该优先级下的最大风向标准偏差

### 重构任务
- **model_dir**: 训练模型的存储目录
- **priority**: 具体任务优先级
- **variables**: 重构变量（通常为["windspeed"]）
- **target_mast/source_mast**: 目标和源测风塔
- **speed_correlation**: 风速相关系数
- **direction_std**: 风向标准偏差
- **data_coverage_days**: 有效数据覆盖天数

## 相关文件

- **配置类型**: `src/Types/ReconstructCrossConfig.jl`
- **处理命令**: [process reconstruct-cross](../process/reconstruct-cross.md)
- **训练配置**: [recommend train-reconstruct-cross](train-reconstruct-cross.md)

## 生成的配置用途

生成的配置文件用于：

1. **跨塔重构**: `julia bin/CleanMast.jl process reconstruct-cross ./reconstruct-cross.toml`
2. **质量控制**: 基于模型性能自动选择最佳重构策略
3. **数据完整性**: 最大化重构后的数据覆盖率
