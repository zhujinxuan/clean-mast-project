# process clean

## 概述

应用数据清理规则，包括范围验证、层差检查和结冰检测。

## 语法

```bash
julia bin/CleanMast.jl process clean <配置文件路径>
```

## 前置条件

- 必须先完成 `project parse-sensors` 步骤
- 存在 `process-clean.toml` 配置文件

## 配置文件格式 (TOML)

### 基本结构

```toml
[[masts]]
name = "测风塔名称"
rules = "清理规则文件路径"

    [masts.input]
    sensors = "输入传感器配置文件"
    data = "输入数据文件"

    [masts.output]
    sensors = "输出传感器配置文件"
    data = "输出数据文件"
```

### 配置参数

- **name**: 测风塔唯一标识符
- **rules**: 清理规则配置文件路径 (如 `"formats/clean/default.toml"`)
- **input.sensors**: 输入传感器元数据文件 (`.toml` 格式)
- **input.data**: 输入时间序列数据文件 (`.csv` 格式)
- **output.sensors**: 输出传感器元数据文件 (`.yaml` 格式)
- **output.data**: 输出时间序列数据文件 (`.csv` 格式)

### 完整配置示例

```toml
[[masts]]
name = "测风塔-001"
rules = "formats/clean/default.toml"

    [masts.output]
    sensors = "./clean/测风塔-001.sensors.yaml"
    data = "./clean/测风塔-001.csv"

    [masts.input]
    sensors = "./raw/测风塔-001.sensors.toml"
    data = "./raw/测风塔-001.csv"

[[masts]]
name = "测风塔-002"
rules = "formats/clean/default.toml"

    [masts.output]
    sensors = "./clean/测风塔-002.sensors.yaml"
    data = "./clean/测风塔-002.csv"

    [masts.input]
    sensors = "./raw/测风塔-002.sensors.toml"
    data = "./raw/测风塔-002.csv"
```

## 输入文件

- **传感器配置**: `.toml` 格式，包含传感器定义和元数据
- **时间序列数据**: `.csv` 格式，包含原始测风塔观测数据

## 输出文件

- `clean/<测风塔名称>.csv`: 清理后的时间序列数据
- `clean/<测风塔名称>.sensors.yaml`: 更新的传感器元数据
- `process-stats/clean-<测风塔名称>.yaml`: 清理统计信息

## 配置生成

使用 `recommend` 命令生成配置文件：

```bash
julia bin/CleanMast.jl recommend process-clean projects/my-windfarm
```

## 下一步操作

数据清理完成后，可以执行：

1. **生成下一步配置**: `julia bin/CleanMast.jl recommend tower-shading projects/my-windfarm`
2. **执行塔影校正**: `julia bin/CleanMast.jl process tower-shading projects/my-windfarm/tower-shading.toml`