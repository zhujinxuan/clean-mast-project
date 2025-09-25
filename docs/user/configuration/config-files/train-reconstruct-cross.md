# train-reconstruct-cross.toml 配置文件

## 概述

`train-reconstruct-cross.toml` 定义跨测风塔训练配置。分析所有测风塔间的相关性并训练跨塔重构模型，用于测风塔间的数据重构。

## 基本结构

```toml
# 测风塔数据源配置
[[masts]]
name = "测风塔名称"
[masts.input]
data = "输入数据文件路径"
sensors = "输入传感器配置路径"

# 训练参数配置
[train]
output_dir = "输出目录"
min_overlap_days = 最小重叠天数
min_correlation = 最小相关系数
max_std_deviation = 最大标准差
max_abs_offset = 最大绝对偏移
min_data_points = 最小数据点数
exclude_nan_results = 是否排除NaN结果
```

## 配置参数

### 测风塔配置 ([[masts]])

#### 必需参数

**name** (字符串)
- 测风塔标识符
- 必须与其他配置文件中的名称一致

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

### 训练参数配置 ([train])

#### 必需参数

**output_dir** (字符串)
- 训练结果保存目录

```toml
output_dir = "./train-reconstruct-cross"
```

#### 可选参数

**min_overlap_days** (浮点数)
- 模型训练所需的最小重叠天数
- 默认值：90.0

```toml
min_overlap_days = 90.0
```

**min_data_points** (整数)
- 训练所需的最小并发数据点数
- 默认值：100

```toml
min_data_points = 200
```

**min_correlation** (浮点数)
- 风速模型的最小相关系数
- 默认值：0.0（训练时宽松）

```toml
min_correlation = 0.7
```

**max_std_deviation** (浮点数)
- 风向模型的最大标准差
- 默认值：Inf（训练时宽松）

```toml
max_std_deviation = 45.0
```

**max_abs_offset** (浮点数)
- 风向模型的最大绝对偏移
- 默认值：Inf（训练时宽松）

```toml
max_abs_offset = 45.0
```

**exclude_nan_results** (布尔值)
- 是否排除NaN/Inf结果
- 默认值：true

```toml
exclude_nan_results = true
```

## 完整配置示例

```toml
# 测风塔数据源
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

# 训练参数
[train]
output_dir = "./train-reconstruct-cross"
min_overlap_days = 90.0
min_data_points = 200
min_correlation = 0.7
max_std_deviation = 45.0
max_abs_offset = 45.0
exclude_nan_results = true
```

## 训练输出

训练完成后会在 `output_dir` 目录下生成：
- 跨塔模型文件（用于重构）
- 训练结果统计文件
- 相关性分析报告

## 配置生成

建议使用推荐命令自动生成配置：

```bash
# 生成跨塔训练配置
julia bin/CleanMast.jl recommend train-reconstruct-cross projects/my-windfarm
```