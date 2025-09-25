# process-clean.toml 配置文件

## 概述

`process-clean.toml` 定义数据清理的规则和参数。数据清理用于识别和处理异常值、错误数据和不合理的测量值。

## 基本结构

```toml
# 测风塔数据清理配置
[[masts]]
name = "数据源名称"
rules = "清理规则文件路径"

[masts.input]
data = "输入数据文件路径"
sensors = "输入传感器配置路径"

[masts.output]
data = "输出数据文件路径"
sensors = "输出传感器配置路径"
```

## 配置参数

### 测风塔配置 ([[masts]])

#### 必需参数

**name** (字符串)
- 测风塔的唯一标识符
- 必须与 `parse-sensors.toml` 中的名称一致

```toml
name = "pn-002824"
```

**rules** (字符串)
- 清理规则配置文件路径
- 定义各种数据验证和清理规则

```toml
rules = "formats/clean/default.toml"
```

**input** (表格)
- 输入数据文件和传感器配置文件
- 通常来自 `raw/` 目录（parse-sensors步骤的输出）

```toml
[masts.input]
data = "./raw/pn-002824.csv"
sensors = "./raw/pn-002824.sensors.toml"
```

**output** (表格)
- 清理后数据的输出路径
- 通常输出到 `clean/` 目录

```toml
[masts.output]
data = "./clean/pn-002824.csv"
sensors = "./clean/pn-002824.sensors.yaml"
```

## 清理规则配置文件

清理规则文件定义了具体的数据清理规则，请参考：

- `formats/clean/default.toml` - 默认NRG测风塔清理规则
- `formats/clean/lidar.toml` - 激光雷达清理规则

## 完整配置示例

### 单测风塔配置
```toml
[[masts]]
name = "pn-002824"
rules = "formats/clean/default.toml"

[masts.input]
data = "./raw/pn-002824.csv"
sensors = "./raw/pn-002824.sensors.toml"

[masts.output]
data = "./clean/pn-002824.csv"
sensors = "./clean/pn-002824.sensors.yaml"
```

### 多测风塔配置
```toml
[[masts]]
name = "pn-002824"
rules = "formats/clean/default.toml"

[masts.input]
data = "./raw/pn-002824.csv"
sensors = "./raw/pn-002824.sensors.toml"

[masts.output]
data = "./clean/pn-002824.csv"
sensors = "./clean/pn-002824.sensors.yaml"

[[masts]]
name = "pn-013945"
rules = "formats/clean/default.toml"

[masts.input]
data = "./raw/pn-013945.csv"
sensors = "./raw/pn-013945.sensors.toml"

[masts.output]
data = "./clean/pn-013945.csv"
sensors = "./clean/pn-013945.sensors.yaml"
```

## 配置生成

建议使用推荐命令自动生成配置：

```bash
# 生成标准清理配置
julia bin/CleanMast.jl recommend process-clean projects/my-windfarm
```