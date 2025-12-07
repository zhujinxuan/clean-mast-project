# train-meso.toml 配置文件

## 概述

`train-meso.toml` 定义中尺度模型训练配置。训练测风塔数据与中尺度数据之间的相关性模型，用于后续的长期数据重构。

## 基本结构

```toml
# 中尺度数据源配置
[[mesos]]
name = "中尺度数据名称"
[mesos.input]
data = "中尺度数据文件路径"
sensors = "中尺度传感器配置路径"

# 测风塔数据源配置
[[masts]]
name = "测风塔名称"
[masts.input]
data = "测风塔数据文件路径"
sensors = "测风塔传感器配置路径"

# 模型训练配置
[[models]]
mast_name = "测风塔名称"
meso_name = "中尺度数据名称"
method = "训练方法"
output = "模型输出路径"
```

## 配置参数

### 中尺度数据配置 ([[mesos]])

**name** (字符串)
- 中尺度数据源标识符
- 必须与 `parse-sensors.toml` 中的名称一致

```toml
name = "era5-002824"
```

**input** (表格)
- 中尺度数据文件和传感器配置文件
- 通常来自 `raw/` 目录

```toml
[mesos.input]
data = "./raw/era5-002824.csv"
sensors = "./raw/era5-002824.sensors.toml"
```

### 测风塔数据配置 ([[masts]])

**name** (字符串)
- 测风塔标识符
- 必须与其他配置文件中的名称一致

```toml
name = "pn-002824"
```

**input** (表格)
- 测风塔数据文件和传感器配置文件
- 通常来自 `tower-shading/` 目录

```toml
[masts.input]
data = "./tower-shading/pn-002824.csv"
sensors = "./tower-shading/pn-002824.sensors.yaml"
```

### 模型训练配置 ([[models]])

**mast_name** (字符串)
- 对应的测风塔名称

```toml
mast_name = "pn-002824"
```

**meso_name** (字符串)
- 对应的中尺度数据名称

```toml
meso_name = "era5-002824"
```

**method** (字符串)
- 训练方法，支持以下选项：
  - `"16-sector"` - 16扇区风速模型（用于代表年订正）
  - `"1-sector"` - 单扇区风速模型（用于数据重构）
  - `"constant-offset"` - 恒定偏移风向模型（用于代表年订正）

```toml
method = "16-sector"
```

**output** (字符串)
- 训练后模型的保存路径（.jld2格式）

```toml
output = "./meso-models/pn-002824/era5-002824/windspeed/16-sector.jld2"
```

## 完整配置示例

### 基础训练配置
```toml
# 中尺度数据
[[mesos]]
name = "era5-002824"
[mesos.input]
data = "./raw/era5-002824.csv"
sensors = "./raw/era5-002824.sensors.toml"

# 测风塔数据
[[masts]]
name = "pn-002824"
[masts.input]
data = "./tower-shading/pn-002824.csv"
sensors = "./tower-shading/pn-002824.sensors.yaml"

# 风速模型训练
[[models]]
mast_name = "pn-002824"
meso_name = "era5-002824"
method = "16-sector"
output = "./meso-models/pn-002824/era5-002824/windspeed/16-sector.jld2"

[[models]]
mast_name = "pn-002824"
meso_name = "era5-002824"
method = "1-sector"
output = "./meso-models/pn-002824/era5-002824/windspeed/1-sector.jld2"

# 风向模型训练
[[models]]
mast_name = "pn-002824"
meso_name = "era5-002824"
method = "constant-offset"
output = "./meso-models/pn-002824/era5-002824/winddirection/constant-offset.jld2"
```

## 模型训练方法

### 风速模型
- **16-sector**: 按16个风向扇区分别训练风速相关性模型（用于代表年订正）
- **1-sector**: 不分风向扇区的整体风速相关性模型（用于数据重构）

### 风向模型
- **constant-offset**: 训练测风塔与中尺度数据间的恒定风向偏移（用于代表年订正）

## 配置生成

建议使用推荐命令自动生成配置：

```bash
# 生成中尺度模型训练配置
julia bin/CleanMast.jl recommend train-meso projects/my-windfarm
```