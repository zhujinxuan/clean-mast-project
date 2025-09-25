# tower-shading.toml 配置文件

## 概述

`tower-shading.toml` 定义塔影校正配置。塔影校正处理相近高度（2米内）的风速传感器，合并数据以处理塔影效应。

## 基本结构

```toml
# 测风塔塔影校正配置
[[masts]]
name = "数据源名称"

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
- 必须与 `process-clean.toml` 中的名称一致

```toml
name = "pn-002824"
```

**input** (表格)
- 输入数据文件和传感器配置文件
- 通常来自 `clean/` 目录（process-clean步骤的输出）

```toml
[masts.input]
data = "./clean/pn-002824.csv"
sensors = "./clean/pn-002824.sensors.yaml"
```

**output** (表格)
- 塔影校正后数据的输出路径
- 通常输出到 `tower-shading/` 目录

```toml
[masts.output]
data = "./tower-shading/pn-002824.csv"
sensors = "./tower-shading/pn-002824.sensors.yaml"
```

## 完整配置示例

### 单测风塔配置
```toml
[[masts]]
name = "pn-002824"

[masts.input]
data = "./clean/pn-002824.csv"
sensors = "./clean/pn-002824.sensors.yaml"

[masts.output]
data = "./tower-shading/pn-002824.csv"
sensors = "./tower-shading/pn-002824.sensors.yaml"
```

### 多测风塔配置
```toml
[[masts]]
name = "pn-002824"

[masts.input]
data = "./clean/pn-002824.csv"
sensors = "./clean/pn-002824.sensors.yaml"

[masts.output]
data = "./tower-shading/pn-002824.csv"
sensors = "./tower-shading/pn-002824.sensors.yaml"

[[masts]]
name = "pn-013945"

[masts.input]
data = "./clean/pn-013945.csv"
sensors = "./clean/pn-013945.sensors.yaml"

[masts.output]
data = "./tower-shading/pn-013945.csv"
sensors = "./tower-shading/pn-013945.sensors.yaml"
```

## 塔影校正处理

塔影校正会自动：
- 识别相近高度（2米内）的风速传感器
- 合并传感器数据以减少塔影效应
- 保持风向和其他传感器数据不变
- 更新传感器配置以反映合并后的传感器

## 配置生成

建议使用推荐命令自动生成配置：

```bash
# 生成塔影校正配置
julia bin/CleanMast.jl recommend tower-shading projects/my-windfarm
```