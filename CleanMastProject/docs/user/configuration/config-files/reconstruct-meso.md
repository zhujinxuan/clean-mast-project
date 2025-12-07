# reconstruct-meso.toml 配置文件

## 概述

`reconstruct-meso.toml` 定义中尺度重构配置。使用训练好的模型，用中尺度数据填补剩余的数据缺失。

## 基本结构

```toml
# 中尺度数据源配置
[[mesos]]
name = "中尺度数据名称"
[mesos.input]
data = "中尺度数据文件路径"
sensors = "中尺度传感器配置路径"

# 测风塔重构配置
[[masts]]
name = "测风塔名称"

[masts.input]
data = "输入数据文件路径"
sensors = "输入传感器配置路径"

[masts.output]
data = "输出数据文件路径"
sensors = "输出传感器配置路径"

[masts.time_range]
min = 开始时间
max = 结束时间

[masts.models.windspeed]
method = "风速重构方法"
model_file = "风速模型文件路径"
meso_name = "中尺度数据名称"

[masts.models.winddirection]
method = "风向重构方法"
model_file = "风向模型文件路径"
meso_name = "中尺度数据名称"
```

## 配置参数

### 中尺度数据配置 ([[mesos]])

与 `train-meso.toml` 中的配置相同，指定用于重构的中尺度数据源。

### 测风塔重构配置 ([[masts]])

#### 必需参数

**name** (字符串)
- 测风塔标识符

```toml
name = "pn-002824"
```

**input** (表格)
- 输入数据文件和传感器配置文件
- 通常来自 `reconstruct-single/` 或 `reconstruct-cross/` 目录

```toml
[masts.input]
data = "./reconstruct-single/pn-002824.csv"
sensors = "./reconstruct-single/pn-002824.sensors.yaml"
```

**output** (表格)
- 中尺度重构后数据的输出路径
- 通常输出到 `reconstruct-meso/` 目录

```toml
[masts.output]
data = "./reconstruct-meso/pn-002824.csv"
sensors = "./reconstruct-meso/pn-002824.sensors.yaml"
```

**time_range** (表格)
- 指定重构的时间范围

```toml
[masts.time_range]
min = 2024-01-01T00:00:00.000Z
max = 2025-01-31T23:59:59.000Z
```

**models** (表格)
- 指定用于重构的模型配置

#### 风速模型配置
```toml
[masts.models.windspeed]
method = "1-sector"
model_file = "./meso-models/pn-002824/era5-002824/windspeed/1-sector.jld2"
meso_name = "era5-002824"
```

#### 风向模型配置
```toml
[masts.models.winddirection]
method = "constant-offset"
model_file = "./meso-models/pn-002824/era5-002824/winddirection/constant-offset.jld2"
meso_name = "era5-002824"
```

## 完整配置示例

```toml
# 中尺度数据
[[mesos]]
name = "era5-002824"
[mesos.input]
data = "./raw/era5-002824.csv"
sensors = "./raw/era5-002824.sensors.toml"

# 测风塔重构
[[masts]]
name = "pn-002824"

[masts.input]
data = "./reconstruct-single/pn-002824.csv"
sensors = "./reconstruct-single/pn-002824.sensors.yaml"

[masts.output]
data = "./reconstruct-meso/pn-002824.csv"
sensors = "./reconstruct-meso/pn-002824.sensors.yaml"

[masts.time_range]
min = 2024-01-01T00:00:00.000Z
max = 2025-01-31T23:59:59.000Z

[masts.models.windspeed]
method = "1-sector"
model_file = "./meso-models/pn-002824/era5-002824/windspeed/1-sector.jld2"
meso_name = "era5-002824"

[masts.models.winddirection]
method = "constant-offset"
model_file = "./meso-models/pn-002824/era5-002824/winddirection/constant-offset.jld2"
meso_name = "era5-002824"
```

## 重构模型选择

### 风速重构
- **1-sector**: 使用单扇区模型进行风速重构

### 风向重构
- **constant-offset**: 使用恒定偏移模型进行风向重构

## 配置生成

建议使用推荐命令自动生成配置：

```bash
# 生成中尺度重构配置
julia bin/CleanMast.jl recommend reconstruct-meso projects/my-windfarm
```