# process reconstruct-meso

## 概述

使用训练好的中尺度模型重构剩余的数据缺口。

## 语法

```bash
julia bin/CleanMast.jl process reconstruct-meso <配置文件路径>
```

## 前置条件

- 必须先完成 `process train-meso` 步骤
- 存在 `reconstruct-meso.toml` 配置文件
- 存在训练好的中尺度模型文件

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
    start_time = "重构开始时间"
    end_time = "重构结束时间"
    [masts.models]
        [masts.models.windspeed]
        method = "风速重构方法"
        meso_name = "中尺度数据源"
        model_file = "风速模型文件路径"
        [masts.models.winddirection]
        method = "风向重构方法"
        meso_name = "中尺度数据源"
        model_file = "风向模型文件路径"
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
- **output.sensors**: 输出传感器元数据文件
- **output.data**: 输出时间序列数据文件
- **time_range.start_time**: 重构开始时间 (ISO格式)
- **time_range.end_time**: 重构结束时间 (ISO格式)

#### 模型配置 (`models`)
- **windspeed.method**: 风速重构方法 (`"16-sector"` 或 `"1-sector"`)
- **windspeed.meso_name**: 对应的中尺度数据源名称
- **windspeed.model_file**: 训练好的风速模型文件路径 (`.jld2` 格式)
- **winddirection.method**: 风向重构方法 (`"constant-offset"`)
- **winddirection.meso_name**: 对应的中尺度数据源名称
- **winddirection.model_file**: 训练好的风向模型文件路径 (`.jld2` 格式)

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
    [masts.output]
    sensors = "./reconstruct-meso/测风塔-001.sensors.yaml"
    data = "./reconstruct-meso/测风塔-001.csv"
    [masts.time_range]
    start_time = "1980-01-01T00:00:00"
    end_time = "2020-12-31T23:50:00"
    [masts.models]
        [masts.models.windspeed]
        method = "16-sector"
        meso_name = "era5-site1"
        model_file = "./meso-models/测风塔-001/era5-site1/windspeed/16-sector.jld2"
        [masts.models.winddirection]
        method = "constant-offset"
        meso_name = "era5-site1"
        model_file = "./meso-models/测风塔-001/era5-site1/winddirection/constant-offset.jld2"
```

## 输入文件

- **测风塔数据**: 来自 reconstruct-single 步骤的传感器配置和时间序列数据
- **中尺度数据**: 原始中尺度再分析数据的传感器配置和时间序列数据
- **模型文件**: 来自 train-meso 步骤的训练好的 `.jld2` 模型文件

## 输出文件

- `reconstruct-meso/<测风塔名称>.csv`: 中尺度重构后的完整数据
- `reconstruct-meso/<测风塔名称>.sensors.yaml`: 更新的传感器元数据
- `process-stats/reconstruct-meso-<测风塔名称>.yaml`: 重构统计和质量信息

## 配置生成

使用 `recommend` 命令生成配置文件：

```bash
julia bin/CleanMast.jl recommend reconstruct-meso projects/my-windfarm
```

## 下一步操作

中尺度重构完成后，可以执行：

1. **质量评估**: 检查重构质量和不确定度
2. **生成下一步配置**: `julia bin/CleanMast.jl recommend representative-year projects/my-windfarm`
3. **执行代表年校准**: `julia bin/CleanMast.jl process representative-year projects/my-windfarm/representative-year.toml`