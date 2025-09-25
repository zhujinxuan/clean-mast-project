# process reconstruct-single

## 概述

使用单测风塔内传感器相关性填补数据缺口。

## 语法

```bash
julia bin/CleanMast.jl process reconstruct-single <配置文件路径>
```

## 前置条件

- 必须先完成 `process tower-shading` 步骤
- 存在 `reconstruct-single.toml` 配置文件

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
- **input.sensors**: 输入传感器元数据文件 (`.yaml` 格式，来自 tower-shading)
- **input.data**: 输入时间序列数据文件 (`.csv` 格式，来自 tower-shading)
- **output.sensors**: 输出传感器元数据文件 (`.yaml` 格式)
- **output.data**: 输出时间序列数据文件 (`.csv` 格式)

### 完整配置示例

```toml
[[masts]]
name = "测风塔-001"

    [masts.input]
    sensors = "./tower-shading/测风塔-001.sensors.yaml"
    data = "./tower-shading/测风塔-001.csv"

    [masts.output]
    sensors = "./reconstruct-single/测风塔-001.sensors.yaml"
    data = "./reconstruct-single/测风塔-001.csv"

[[masts]]
name = "测风塔-002"

    [masts.input]
    sensors = "./tower-shading/测风塔-002.sensors.yaml"
    data = "./tower-shading/测风塔-002.csv"

    [masts.output]
    sensors = "./reconstruct-single/测风塔-002.sensors.yaml"
    data = "./reconstruct-single/测风塔-002.csv"
```

## 输入文件

- **传感器配置**: `.yaml` 格式，包含塔影校正后的传感器定义和元数据
- **时间序列数据**: `.csv` 格式，包含塔影校正后的测风塔观测数据

## 输出文件

- `reconstruct-single/<测风塔名称>.csv`: 重构后的数据
- `reconstruct-single/<测风塔名称>.sensors.yaml`: 更新的传感器元数据
- `process-stats/reconstruct-single-<测风塔名称>.yaml`: 重构统计信息

## 配置生成

使用 `recommend` 命令生成配置文件：

```bash
julia bin/CleanMast.jl recommend reconstruct-single projects/my-windfarm
```

## 下一步操作

单测风塔重构完成后，可以执行：

1. **质量评估**: `julia bin/CleanMast.jl analyze reconstruct-single projects/my-windfarm`
2. **生成下一步配置**: `julia bin/CleanMast.jl recommend train-meso projects/my-windfarm`
3. **执行中尺度训练**: `julia bin/CleanMast.jl process train-meso projects/my-windfarm/train-meso.toml`