# process representative-year

## 概述

使用16扇区方法进行代表年校准，分析长期气象模式，识别代表性条件，应用校准因子生成代表年数据集。

## 语法

```bash
julia bin/CleanMast.jl process representative-year <配置文件路径>
```

## 前置条件

- 必须先完成 `process reconstruct-meso` 步骤
- 存在 `representative-year.toml` 配置文件
- 存在训练好的16扇区中尺度模型文件

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
    [masts.output]
    sensors = "输出传感器配置文件"
    data = "输出数据文件"
    [masts.time_range]
    min = "开始时间"
    max = "结束时间"
    [masts.meso_model]
    method = "16-sector"
    meso_name = "中尺度数据源"
    model_file = "16扇区模型文件路径"
```

### 配置参数

#### 中尺度数据源 (`mesos`)
- **name**: 中尺度数据源唯一标识符
- **input.sensors**: 中尺度传感器元数据文件 (`.toml` 格式)
- **input.data**: 中尺度时间序列数据文件 (`.csv` 格式)

#### 测风塔配置 (`masts`)
- **name**: 测风塔唯一标识符
- **input.sensors**: 输入传感器元数据文件 (来自 reconstruct-meso)
- **input.data**: 输入时间序列数据文件 (来自 reconstruct-meso)
- **output.sensors**: 输出传感器元数据文件
- **output.data**: 输出时间序列数据文件
- **time_range.min**: 代表年开始时间 (ISO格式)
- **time_range.max**: 代表年结束时间 (ISO格式)

#### 中尺度模型 (`meso_model`)
- **method**: 必须为 `"16-sector"` (16扇区方法进行方向性校准)
- **meso_name**: 对应的中尺度数据源名称
- **model_file**: 训练好的16扇区风速模型文件路径 (`.jld2` 格式)

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
    sensors = "./reconstruct-meso/测风塔-001.sensors.yaml"
    data = "./reconstruct-meso/测风塔-001.csv"
    [masts.output]
    sensors = "./representative-year/测风塔-001.sensors.yaml"
    data = "./representative-year/测风塔-001.csv"
    [masts.time_range]
    min = 2024-01-01T00:00:00.000Z
    max = 2024-12-31T23:50:00.000Z
    [masts.meso_model]
    method = "16-sector"
    meso_name = "era5-site1"
    model_file = "./meso-models/测风塔-001/era5-site1/windspeed/16-sector.jld2"

[[masts]]
name = "测风塔-002"
    [masts.input]
    sensors = "./reconstruct-meso/测风塔-002.sensors.yaml"
    data = "./reconstruct-meso/测风塔-002.csv"
    [masts.output]
    sensors = "./representative-year/测风塔-002.sensors.yaml"
    data = "./representative-year/测风塔-002.csv"
    [masts.time_range]
    min = 2024-01-01T00:00:00.000Z
    max = 2024-12-31T23:50:00.000Z
    [masts.meso_model]
    method = "16-sector"
    meso_name = "era5-site1"
    model_file = "./meso-models/测风塔-002/era5-site1/windspeed/16-sector.jld2"
```

## 16扇区校准方法

代表年校准使用16扇区方法进行方向性分析：

- **扇区分析**: 将360°分为16个22.5°扇区，每个扇区独立校准
- **长期模式识别**: 基于中尺度数据分析每个扇区的长期气象模式
- **校准因子计算**: 为每个扇区计算具体的校准因子
- **方向性校正**: 考虑不同风向下的地形和气象特征差异

## 输入文件

- **测风塔数据**: 来自 reconstruct-meso 步骤的传感器配置和时间序列数据
- **中尺度数据**: 原始中尺度再分析数据的传感器配置和时间序列数据
- **16扇区模型**: 来自 train-meso 步骤训练的16扇区风速模型 (`.jld2` 格式)

## 输出文件

- `representative-year/<测风塔名称>.csv`: 代表年校准后的时间序列数据
- `representative-year/<测风塔名称>.sensors.yaml`: 更新的传感器元数据
- `process-stats/representative-year-<测风塔名称>.yaml`: 校准统计信息

## 配置生成

使用 `recommend` 命令生成配置文件：

```bash
julia bin/CleanMast.jl recommend representative-year projects/my-windfarm
```

## 下一步操作

代表年校准完成后，可以执行：

1. **生成风机时间序列配置**: `julia bin/CleanMast.jl recommend wt-timeseries projects/my-windfarm`
2. **导出Meteodyn时间序列**: `julia bin/CleanMast.jl process wt-timeseries projects/my-windfarm/wt-timeseries.toml`