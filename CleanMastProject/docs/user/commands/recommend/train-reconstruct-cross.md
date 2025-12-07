# recommend train-reconstruct-cross

## 概述

生成跨测风塔重构模型训练配置文件。分析多个测风塔之间的相关性，为缺失数据较多的测风塔建立基于其他测风塔的重构模型。

## 语法

```bash
julia bin/CleanMast.jl recommend train-reconstruct-cross <项目目录>
```

## 实现位置

**核心实现**: `src/TrainReconstructCross/RecommendTrainReconstructCrossCommand.jl`

## 前置条件

- 必须先完成 `process reconstruct-single` 步骤
- 项目中存在多个测风塔的单塔重构数据
- 测风塔之间有足够的时间重叠数据

## 功能描述

### 1. 测风塔数据分析
- 扫描 `reconstruct-single/` 目录中的所有测风塔数据
- 分析每个测风塔的数据覆盖率和质量
- 识别需要跨塔重构的测风塔

### 2. 配置参数设定
- **最小重叠天数**: 默认90天，确保足够的训练数据
- **最小相关系数**: 默认0.7，保证重构质量
- **最大标准偏差**: 默认45.0，控制风向偏差范围
- **最小数据点数**: 默认200点，确保统计显著性

### 3. 自动配置生成
- 创建所有测风塔的输入数据配置
- 设置训练参数和质量控制标准
- 指定模型输出目录结构

## 输出配置示例

基于 `projects/pn-3masts/train-reconstruct-cross.toml`:

```toml
# 测风塔数据源配置
[[masts]]
name = "pn-002824"
    [masts.input]
    data = "./reconstruct-single/pn-002824.csv"
    sensors = "./reconstruct-single/pn-002824.sensors.yaml"

[[masts]]
name = "pn-013945"
    [masts.input]
    data = "./reconstruct-single/pn-013945.csv"
    sensors = "./reconstruct-single/pn-013945.sensors.yaml"

[[masts]]
name = "pn-014576"
    [masts.input]
    data = "./reconstruct-single/pn-014576.csv"
    sensors = "./reconstruct-single/pn-014576.sensors.yaml"

# 训练参数配置
[train]
min_overlap_days = 90.0          # 最小重叠天数
max_std_deviation = 45.0         # 最大风向标准偏差
min_data_points = 200            # 最小数据点数
output_dir = "./train-reconstruct-cross"  # 输出目录
max_abs_offset = 45.0            # 最大绝对偏移角度
min_correlation = 0.7            # 最小相关系数
exclude_nan_results = true       # 排除无效结果
```

## 配置参数说明

### 数据质量控制
- `min_overlap_days`: 测风塔对之间的最小有效重叠天数
- `min_data_points`: 训练模型所需的最小数据点数
- `exclude_nan_results`: 是否排除产生无效结果的模型

### 相关性要求
- `min_correlation`: 风速相关系数的最小阈值
- `max_std_deviation`: 风向偏差的最大标准偏差
- `max_abs_offset`: 平均风向偏移的最大绝对值

### 输出设置
- `output_dir`: 训练结果和模型的存储目录

## 相关文件

- **配置类型**: `src/Types/TrainReconstructCrossConfig.jl`
- **处理命令**: [process train-reconstruct-cross](../process/train-reconstruct-cross.md)

## 生成的配置用途

生成的配置文件用于：

1. **模型训练**: `julia bin/CleanMast.jl process train-reconstruct-cross ./train-reconstruct-cross.toml`
2. **相关性分析**: 建立测风塔间的统计关系模型
3. **质量评估**: 评估跨塔重构的可行性和精度

