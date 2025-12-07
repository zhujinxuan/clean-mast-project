# reconstruct-single.toml 配置文件

## 概述

`reconstruct-single.toml` 定义单测风塔重构配置。使用同一测风塔上传感器间的相关性来填补数据缺失。

## 基本结构

```toml
# 单测风塔重构配置
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
- 必须与 `tower-shading.toml` 中的名称一致

```toml
name = "pn-002824"
```

**input** (表格)
- 输入数据文件和传感器配置文件
- 通常来自 `tower-shading/` 目录（tower-shading步骤的输出）

```toml
[masts.input]
data = "./tower-shading/pn-002824.csv"
sensors = "./tower-shading/pn-002824.sensors.yaml"
```

**output** (表格)
- 单塔重构后数据的输出路径
- 通常输出到 `reconstruct-single/` 目录

```toml
[masts.output]
data = "./reconstruct-single/pn-002824.csv"
sensors = "./reconstruct-single/pn-002824.sensors.yaml"
```

## 完整配置示例

### 单测风塔配置
```toml
[[masts]]
name = "pn-002824"

[masts.input]
data = "./tower-shading/pn-002824.csv"
sensors = "./tower-shading/pn-002824.sensors.yaml"

[masts.output]
data = "./reconstruct-single/pn-002824.csv"
sensors = "./reconstruct-single/pn-002824.sensors.yaml"
```

### 多测风塔配置
```toml
[[masts]]
name = "pn-002824"

[masts.input]
data = "./tower-shading/pn-002824.csv"
sensors = "./tower-shading/pn-002824.sensors.yaml"

[masts.output]
data = "./reconstruct-single/pn-002824.csv"
sensors = "./reconstruct-single/pn-002824.sensors.yaml"

[[masts]]
name = "pn-013945"

[masts.input]
data = "./tower-shading/pn-013945.csv"
sensors = "./tower-shading/pn-013945.sensors.yaml"

[masts.output]
data = "./reconstruct-single/pn-013945.csv"
sensors = "./reconstruct-single/pn-013945.sensors.yaml"
```

## 单塔重构处理

单塔重构会自动：
- 分析同一测风塔上不同高度传感器间的相关性
- 使用高度间的风切变关系重构缺失的风速数据
- 使用风向相关性重构缺失的风向数据

## 配置生成

建议使用推荐命令自动生成配置：

```bash
# 生成单塔重构配置
julia bin/CleanMast.jl recommend reconstruct-single projects/my-windfarm
```