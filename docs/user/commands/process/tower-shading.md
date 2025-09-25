# process tower-shading

## 概述

检测和校正塔影效应，合并相近高度的风速传感器。

## 语法

```bash
julia bin/CleanMast.jl process tower-shading <配置文件路径>
```

## 前置条件

- 必须先完成 `process clean` 步骤
- 存在 `tower-shading.toml` 配置文件

## 配置文件格式 (TOML)

### 基本结构

```toml
[[masts]]
name = "测风塔名称"

    [masts.input]
    sensors = "输入传感器配置文件"
    data = "输入数据文件"

    [masts.output]
    sensors = "输出传感器配置文件"
    data = "输出数据文件"
```

### 配置参数

- **name**: 测风塔唯一标识符
- **input.sensors**: 输入传感器元数据文件 (`.yaml` 格式，来自 process clean)
- **input.data**: 输入时间序列数据文件 (`.csv` 格式，来自 process clean)
- **output.sensors**: 输出传感器元数据文件 (`.yaml` 格式)
- **output.data**: 输出时间序列数据文件 (`.csv` 格式)

### 完整配置示例

```toml
[[masts]]
name = "测风塔-001"

    [masts.output]
    sensors = "./tower-shading/测风塔-001.sensors.yaml"
    data = "./tower-shading/测风塔-001.csv"

    [masts.input]
    sensors = "./clean/测风塔-001.sensors.yaml"
    data = "./clean/测风塔-001.csv"

[[masts]]
name = "测风塔-002"

    [masts.output]
    sensors = "./tower-shading/测风塔-002.sensors.yaml"
    data = "./tower-shading/测风塔-002.csv"

    [masts.input]
    sensors = "./clean/测风塔-002.sensors.yaml"
    data = "./clean/测风塔-002.csv"
```

## 输入文件

- **传感器配置**: `.yaml` 格式，包含清理后的传感器定义和元数据
- **时间序列数据**: `.csv` 格式，包含清理后的测风塔观测数据

## 输出文件

- `tower-shading/<测风塔名称>.csv`: 塔影校正后的数据
- `tower-shading/<测风塔名称>.sensors.yaml`: 更新的传感器配置
- `process-stats/tower-shading-<测风塔名称>.yaml`: 校正统计信息

## 配置生成

使用 `recommend` 命令生成配置文件：

```bash
julia bin/CleanMast.jl recommend tower-shading projects/my-windfarm
```

## 下一步操作

塔影校正完成后，可以执行：

1. **生成下一步配置**: `julia bin/CleanMast.jl recommend reconstruct-single projects/my-windfarm`
2. **执行单塔重构**: `julia bin/CleanMast.jl process reconstruct-single projects/my-windfarm/reconstruct-single.toml`