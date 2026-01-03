# parse-sensors.toml 配置文件

## 概述

`parse-sensors.toml` 定义如何解析原始测量数据文件并将其转换为标准化格式。此配置文件控制传感器数据的解析、列映射和输出生成。

## 基本结构

```toml
# 测风塔数据源
[[masts]]
name = "数据源名称"
input = "原始数据文件.txt"
sensor = "传感器格式文件路径"
# 输出路径自动根据name生成

# 中尺度数据源
[[mesos]]
name = "中尺度数据名称"
input = "中尺度数据文件.txt"
sensor = "中尺度传感器格式文件路径"
# 输出路径自动根据name生成
```

## 配置参数

### 测风塔数据配置 ([[masts]])

#### 必需参数

**name** (字符串)
- 数据源的唯一标识符
- 用于后续处理步骤中引用此数据
- 输出文件会自动基于此字段命名

```toml
name = "pn-002824"
```

**input** (字符串)
- 原始数据文件路径
- 支持相对路径（相对于项目根目录）
- 常见格式：`.txt`, `.csv`, `.dat`

```toml
input = "masts/pn-002824.txt"
```

**sensor** (字符串)
- 传感器格式配置文件路径
- 定义如何解析原始数据列结构
- 通常位于 `formats/sensor/` 目录

```toml
sensor = "formats/sensor/nrg.toml"
```

#### 可选参数

**interpolate** (表格)
- 时间序列插值配置
- 将数据从一个间隔转换为另一个间隔

```toml
[masts.interpolate]
from_minutes = 60  # 从60分钟数据转换
to_minutes = 10    # 到10分钟间隔
```

### 中尺度数据配置 ([[mesos]])

中尺度数据使用与测风塔相同的结构，通常表示再分析数据：

```toml
[[mesos]]
name = "era5-002824"
input = "mesos/era5-002824.txt"
sensor = "formats/sensor/freemeso-meso.toml"
```

## 完整配置示例

### 单测风塔项目
```toml
# 单测风塔配置
[[masts]]
name = "main-tower"
input = "masts/tower_data.txt"
sensor = "formats/sensor/nrg.toml"

[[mesos]]
name = "era5"
input = "mesos/era5_reanalysis.txt"
sensor = "formats/sensor/freemeso-meso.toml"
```

### 多测风塔项目
```toml
# 多测风塔配置
[[masts]]
name = "pn-002824"
input = "masts/pn-002824.txt"
sensor = "formats/sensor/nrg.toml"

[[masts]]
name = "pn-013945"
input = "masts/pn-013945.txt"
sensor = "formats/sensor/nrg.toml"

[[masts]]
name = "pn-014576"
input = "masts/pn-014576.txt"
sensor = "formats/sensor/nrg.toml"

# 对应的中尺度数据
[[mesos]]
name = "era5-002824"
input = "mesos/era5-002824.txt"
sensor = "formats/sensor/freemeso-meso.toml"

[[mesos]]
name = "era5-013945"
input = "mesos/era5-013945.txt"
sensor = "formats/sensor/freemeso-meso.toml"

[[mesos]]
name = "era5-014576"
input = "mesos/era5-014576.txt"
sensor = "formats/sensor/freemeso-meso.toml"
```

## 传感器格式文件

传感器格式文件使用基于模式的匹配来定义如何解析原始数据文件列结构。

### NRG 格式 (formats/sensor/nrg.toml)
```toml
timestamp_column = "#"
timestamp_format = "M/d/yyyy H:mm"

[[columns]]
match = "WS(?<height>\\d+)m(?<direction>[NESW]+)Avg"
format = "WS:{height}m:{direction}:avg"

[[columns]]
match = "WD(?<height>\\d+)m(?<direction>[NESW]+)Avg"
format = "WD:{height}m:{direction}:avg"

[[mappings]]
[mappings.match]
sensorType = "WindSpeed"
[mappings.rule]
sensorType = "WindSpeed"
statType = "avg"
unit = "m/s"

[[mappings]]
[mappings.match]
sensorType = "WindDirection"
[mappings.rule]
sensorType = "WindDirection"
statType = "avg"
unit = "degrees"
```

### 中尺度格式 (formats/sensor/freemeso-meso.toml)
```toml
timestamp_column = "time"
timestamp_format = "yyyy-MM-dd HH:mm:ss"

[[columns]]
match = "(?<var>u|v)(?<height>\\d+)"
format = "{var}:{height}m:N/A:avg"

[[columns]]
match = "(?<var>t)(?<height>\\d+)m"
format = "{var}:{height}m:N/A:avg"

[[mappings]]
[mappings.match]
sensorType = "u"
[mappings.rule]
sensorType = "WindSpeed_U"
statType = "avg"
unit = "m/s"
```

## 输出文件

输出文件自动生成在以下位置：

### 数据文件 (.csv)
标准化时间序列数据保存至 `./raw/{name}.csv`：
- CSV格式，包含时间戳和传感器数据列
- 规律化10分钟间隔（或指定插值）
- 标准化列名和单位

### 传感器配置文件 (.sensors.toml)
传感器元数据保存至 `./raw/{name}.sensors.toml`：
```toml
# 示例传感器配置输出
[[sensors]]
name = "WS:80m:N"
sensorType = "WindSpeed"
height = 80.0
sensorDirection = "N"
unit = "m/s"
statType = "avg"

[[sensors]]
name = "WD:80m:N"
sensorType = "WindDirection"
height = 80.0
sensorDirection = "N"
unit = "degrees"
statType = "avg"
```

## 配置生成

### 方法一：项目初始化
虽然可以手动创建 `parse-sensors.toml`，但建议使用项目初始化功能：

```bash
# 创建新项目，自动生成示例配置
uv run cleanmast init projects/my-windfarm
```

然后编辑生成的 `parse-sensors.toml` 文件以匹配您的数据。

### 方法二：自动推荐配置
如果使用金风 freemeso 作为中尺度数据，且所有测风塔数据遵循 NRG 格式，可以将数据文件按以下结构组织：

```
projects/my-windfarm/
├── masts/
│   ├── tower1.txt
│   ├── tower2.txt
│   └── tower3.txt
└── mesos/
    ├── era5-tower1.txt
    ├── era5-tower2.txt
    └── era5-tower3.txt
```

然后使用推荐命令自动生成配置：

```bash
# 基于现有原始数据文件生成配置
julia bin/CleanMast.jl recommend parse-sensors projects/my-windfarm
```

这会分析您的原始数据文件并自动生成合适的传感器格式配置。

