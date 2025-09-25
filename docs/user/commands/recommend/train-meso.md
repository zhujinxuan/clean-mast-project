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
- **精度**: 通常 R² > 0.8

#### 1扇区线性回归
- **用途**: 简单全方向关系
- **模型**: WS_mast = a × WS_meso + b
- **适用**: 地形简单或数据有限情况

#### 非线性回归（可选）
- **方法**: 多项式、样条、神经网络
- **用途**: 复杂地形或非线性关系
- **计算**: 需要更多训练数据

### 2. 风向模型

#### 常数偏移
- **模型**: WD_mast = WD_meso + offset
- **计算**: 圆形统计平均偏移
- **适用**: 大部分情况

#### 扇区偏移（可选）
- **模型**: WD_mast = WD_meso + offset_sector
- **用途**: 考虑风向相关的地形效应

### 3. 温度/气压模型

#### 线性回归
- **高度校正**: 考虑测量高度差异
- **季节调整**: 可选的季节性参数

## 自动化功能

该命令会自动：

1. **数据匹配分析**
   - 检测测风塔与中尺度数据的时间重叠
   - 评估数据质量和完整性
   - 计算基本相关性统计

2. **模型策略选择**
   - 根据数据量选择合适的模型复杂度
   - 基于地形复杂度推荐扇区数量
   - 设置交叉验证策略

3. **性能预期估算**
   - 预测各模型的可能精度
   - 识别潜在的问题区域
   - 建议优化方向

## 下一步操作

配置生成后，可以执行以下步骤：

1. **检查配置**: 验证中尺度数据源和模型参数
2. **执行训练**: `julia bin/CleanMast.jl process train-meso ./project/train-meso.toml`
3. **检查训练结果**: 查看 `meso-models/train-meso-results.toml` 中的相关性统计
4. **验证模型**: 检查训练结果和模型性能统计
5. **生成下一步配置**: `julia bin/CleanMast.jl recommend reconstruct-meso ./project`

## 注意事项

- 需要有足够的时间重叠数据（建议 > 6个月）
- 中尺度数据质量直接影响模型性能
- 复杂地形可能需要更多扇区或非线性模型
- 训练完成后应验证模型的适用性和精度