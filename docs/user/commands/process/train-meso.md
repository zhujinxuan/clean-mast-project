# process train-meso

## 概述

训练测风塔与中尺度数据之间的相关模型。

## 语法

```bash
julia bin/CleanMast.jl process train-meso <配置文件路径>
```

## 前置条件

- 必须先完成 `process reconstruct-single` 步骤
- 存在 `train-meso.toml` 配置文件
- 有可用的中尺度再分析数据

## 配置文件格式 (TOML)

### 基本结构

```toml
[[mesos]]
name = "中尺度数据源名称"
    [mesos.input]
    sensors = "中尺度传感器配置文件"
    data = "中尺度数据文件"

[[masts]]
name = "测风塔名称"
    [masts.input]
    sensors = "输入传感器配置文件"
    data = "输入数据文件"

[[models]]
method = "模型类型"
output = "输出模型文件路径"
mast_name = "目标测风塔"
meso_name = "参考中尺度源"
```

### 配置参数

#### 中尺度数据源 (`mesos`)
- **name**: 中尺度数据源唯一标识符
- **input.sensors**: 中尺度传感器元数据文件 (`.toml` 格式)
- **input.data**: 中尺度时间序列数据文件 (`.csv` 格式)

#### 测风塔配置 (`masts`)
- **name**: 测风塔唯一标识符
- **input.sensors**: 输入传感器元数据文件 (来自 reconstruct-single)
- **input.data**: 输入时间序列数据文件 (来自 reconstruct-single)

#### 模型训练任务 (`models`)
- **method**: 训练模型类型
  - `"16-sector"`: 16扇区风速线性回归
  - `"1-sector"`: 全方向风速线性回归
  - `"constant-offset"`: 风向常数偏移校正
- **output**: 训练好的模型保存路径 (`.jld2` 格式)
- **mast_name**: 目标测风塔名称
- **meso_name**: 参考中尺度数据源名称

### 完整配置示例

```toml
[[mesos]]
name = "era5-site1"
    [mesos.input]
    sensors = "./raw/era5-site1.sensors.toml"
    data = "./raw/era5-site1.csv"

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

# 测风塔-001 的训练模型
[[models]]
method = "16-sector"
output = "./meso-models/测风塔-001/era5-site1/windspeed/16-sector.jld2"
mast_name = "测风塔-001"
meso_name = "era5-site1"

[[models]]
method = "1-sector"
output = "./meso-models/测风塔-001/era5-site1/windspeed/1-sector.jld2"
mast_name = "测风塔-001"
meso_name = "era5-site1"

[[models]]
method = "constant-offset"
output = "./meso-models/测风塔-001/era5-site1/winddirection/constant-offset.jld2"
mast_name = "测风塔-001"
meso_name = "era5-site1"

# 测风塔-002 的训练模型
[[models]]
method = "16-sector"
output = "./meso-models/测风塔-002/era5-site1/windspeed/16-sector.jld2"
mast_name = "测风塔-002"
meso_name = "era5-site1"

[[models]]
method = "1-sector"
output = "./meso-models/测风塔-002/era5-site1/windspeed/1-sector.jld2"
mast_name = "测风塔-002"
meso_name = "era5-site1"

[[models]]
method = "constant-offset"
output = "./meso-models/测风塔-002/era5-site1/winddirection/constant-offset.jld2"
mast_name = "测风塔-002"
meso_name = "era5-site1"
```

## 输入文件

- **测风塔数据**: 来自 reconstruct-single 步骤的传感器配置和时间序列数据
- **中尺度数据**: 原始中尺度再分析数据的传感器配置和时间序列数据

## 输出文件

- **模型文件**: `meso-models/<测风塔>/<中尺度源>/windspeed|winddirection/<方法>.jld2`
- **训练结果汇总**: `meso-models/train-meso-results.toml`
- **训练统计**: `meso-models/<测风塔>/stats/<中尺度源>-training-stats.yaml`

### 训练结果汇总文件

`meso-models/train-meso-results.toml` 包含所有测风塔-中尺度对的相关性信息：

```toml
# 训练元数据
[metadata]
training_date = "2025-01-15T10:30:00.000Z"
total_mast_meso_pairs = 4
qualified_pairs = 3

# 测风塔-中尺度相关性结果
[[correlations]]
mast_name = "测风塔-001"
meso_name = "era5-site1"
windspeed_correlation = 0.8895
winddirection_std = 24.54
data_coverage_days = 396.88
model_quality = "high"
```

## 配置生成

使用 `recommend` 命令生成配置文件：

```bash
julia bin/CleanMast.jl recommend train-meso projects/my-windfarm
```

## 下一步操作

中尺度模型训练完成后，可以执行：

1. **检查训练结果**: 查看 `meso-models/train-meso-results.toml` 中的相关性信息
2. **验证模型**: 检查训练结果和模型性能统计
3. **生成下一步配置**: `julia bin/CleanMast.jl recommend reconstruct-meso projects/my-windfarm`
4. **执行中尺度重构**: `julia bin/CleanMast.jl process reconstruct-meso projects/my-windfarm/reconstruct-meso.toml`