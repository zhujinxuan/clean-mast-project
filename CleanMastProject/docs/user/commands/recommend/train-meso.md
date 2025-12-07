# recommend train-meso

## 概述

生成中尺度模型训练的配置文件，建立测风塔观测数据与中尺度再分析数据之间的统计关系模型。

## 语法

```bash
julia bin/CleanMast.jl recommend train-meso <项目目录>
```

## 实现位置

**核心实现**: `src/TrainMeso/RecommendTrainMesoCommand.jl`

## 功能流程

1. **数据源识别**
   - 读取塔影校正配置获取测风塔数据路径
   - 读取 `parse-sensors.toml` 识别中尺度数据源
   - 验证数据时间重叠范围

2. **模型配置生成**
   - 为所有测风塔-中尺度组合创建模型训练条目
   - 配置多种模型类型（16扇区、1扇区、常数偏移）
   - 设置训练参数和验证策略

3. **输出文件**
   - 生成 `train-meso.toml` 配置文件
   - 训练完成后产生 `meso-models/train-meso-results.toml` 结果汇总

## 相关文件

- **配置文件**: train-meso.toml (待创建配置文档)
- **处理命令**: [process train-meso](../process/train-meso.md)
- **配置类型**: `src/Types/TrainMesoConfig.jl`
- **技术实现**: [中尺度重构算法](../../../technical/algorithms/reconstruct-meso.md)

## 输出配置示例

```toml
# train-meso.toml
# 基于实际项目结构: projects/pn-3masts/train-meso.toml
# 为测风塔-中尺度数据组合训练统计关系模型

# 中尺度数据源配置
[[mesos]]
name = "era5-002824"
    [mesos.input]
    data = "./raw/era5-002824.csv"
    sensors = "./raw/era5-002824.sensors.toml"

[[mesos]]
name = "era5-013945"
    [mesos.input]
    data = "./raw/era5-013945.csv"
    sensors = "./raw/era5-013945.sensors.toml"

# 测风塔数据源配置
[[masts]]
name = "pn-002824"
    [masts.input]
    data = "./tower-shading/pn-002824.csv"
    sensors = "./tower-shading/pn-002824.sensors.yaml"

[[masts]]
name = "pn-013945"
    [masts.input]
    data = "./tower-shading/pn-013945.csv"
    sensors = "./tower-shading/pn-013945.sensors.yaml"

# 模型配置 - 为每个测风塔和中尺度数据组合训练模型
# 风速16扇区模型
[[models]]
mast_name = "pn-002824"
meso_name = "era5-002824"
method = "16-sector"
output = "./meso-models/pn-002824/era5-002824/windspeed/16-sector.jld2"

# 风速1扇区模型
[[models]]
mast_name = "pn-002824"
meso_name = "era5-002824"
method = "1-sector"
output = "./meso-models/pn-002824/era5-002824/windspeed/1-sector.jld2"

# 风向常数偏移模型
[[models]]
mast_name = "pn-002824"
meso_name = "era5-002824"
method = "constant-offset"
output = "./meso-models/pn-002824/era5-002824/winddirection/constant-offset.jld2"

# 跨塔训练：使用era5-013945为pn-002824训练模型
[[models]]
mast_name = "pn-002824"
meso_name = "era5-013945"
method = "16-sector"
output = "./meso-models/pn-002824/era5-013945/windspeed/16-sector.jld2"

[[models]]
mast_name = "pn-002824"
meso_name = "era5-013945"
method = "1-sector"
output = "./meso-models/pn-002824/era5-013945/windspeed/1-sector.jld2"

[[models]]
mast_name = "pn-002824"
meso_name = "era5-013945"
method = "constant-offset"
output = "./meso-models/pn-002824/era5-013945/winddirection/constant-offset.jld2"

# ... 更多模型配置 (实际项目中会为所有测风塔-中尺度组合生成)
```

## 生成的模型类型

### 1. 风速模型

#### 16扇区线性回归
- **用途**: 考虑风向相关的地形效应
- **扇区划分**: 每22.5°一个扇区
- **模型**: WS_mast = a_sector × WS_meso + b_sector

#### 1扇区线性回归
- **用途**: 简单全方向关系
- **模型**: WS_mast = a × WS_meso + b


### 2. 风向模型

#### 常数偏移
- **模型**: WD_mast = WD_meso + offset
- **计算**: 圆形统计平均偏移
- **适用**: 大部分情况



## 下一步操作

配置生成后，可以执行以下步骤：

1. **检查配置**: 验证中尺度数据源和模型参数
2. **执行训练**: `julia bin/CleanMast.jl process train-meso ./project/train-meso.toml`
3. **检查训练结果**: 查看 `meso-models/train-meso-results.toml` 中的相关性统计
4. **验证模型**: 检查训练结果和模型性能统计
5. **生成下一步配置**: `julia bin/CleanMast.jl recommend reconstruct-meso ./project`
