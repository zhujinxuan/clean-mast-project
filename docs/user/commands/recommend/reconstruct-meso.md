# recommend reconstruct-meso

## 概述

生成中尺度重构的配置文件，基于训练好的模型使用中尺度数据填补测风塔数据缺失并扩展时间序列。

## 语法

```bash
julia bin/CleanMast.jl recommend reconstruct-meso <项目目录>
```

## 实现位置

**核心实现**: `src/ReconstructMeso/RecommendReconstructMesoCommand.jl`

## 功能流程

1. **模型分析**
   - 读取 `meso-models/train-meso-results.toml` 训练结果汇总
   - 扫描 `meso-models/` 目录下的训练结果
   - 读取模型性能指标和验证统计
   - 评估模型质量和适用性

2. **模型选择**
   - 基于 `train-meso-results.toml` 中的相关性信息选择最佳模型
   - 为每个目标传感器选择最佳模型
   - 比较不同中尺度数据源的性能
   - 配置备用模型和降级策略

3. **重构配置**
   - 设置长期重构的时间范围
   - 配置质量控制参数
   - 生成智能的重构配置

4. **输出文件**
   - 生成 `reconstruct-meso.toml` 配置文件

## 相关文件

- **配置文件**: reconstruct-meso.toml (待创建配置文档)
- **处理命令**: [process reconstruct-meso](../process/reconstruct-meso.md)
- **配置类型**: `src/Types/ReconstructMesoConfig.jl`
- **技术实现**: [中尺度重构算法](../../../technical/algorithms/reconstruct-meso.md)

## 输出配置示例

```toml
# reconstruct-meso.toml
# 基于实际项目结构: projects/pn-3masts/reconstruct-meso.toml
# 使用训练好的模型填补剩余缺失数据

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

# 测风塔重构配置
[[masts]]
name = "pn-002824"

    [masts.input]
    data = "./reconstruct-single/pn-002824.csv"
    sensors = "./reconstruct-single/pn-002824.sensors.yaml"

    [masts.output]
    data = "./reconstruct-meso/pn-002824.csv"
    sensors = "./reconstruct-meso/pn-002824.sensors.yaml"

    # 时间范围配置
    [masts.time_range]
    min = 2024-01-01T00:00:00.000Z
    max = 2025-01-31T23:59:59.000Z

    # 风速重构模型
    [masts.models.windspeed]
    method = "1-sector"
    model_file = "./meso-models/pn-002824/era5-002824/windspeed/1-sector.jld2"
    meso_name = "era5-002824"

    # 风向重构模型
    [masts.models.winddirection]
    method = "constant-offset"
    model_file = "./meso-models/pn-002824/era5-002824/winddirection/constant-offset.jld2"
    meso_name = "era5-002824"

[[masts]]
name = "pn-013945"

    [masts.input]
    data = "./reconstruct-single/pn-013945.csv"
    sensors = "./reconstruct-single/pn-013945.sensors.yaml"

    [masts.output]
    data = "./reconstruct-meso/pn-013945.csv"
    sensors = "./reconstruct-meso/pn-013945.sensors.yaml"

    [masts.time_range]
    min = 2024-01-01T00:00:00.000Z
    max = 2025-01-31T23:59:59.000Z

    # 使用跨塔模型：用era5-002824的中尺度数据为pn-013945重构
    [masts.models.windspeed]
    method = "1-sector"
    model_file = "./meso-models/pn-013945/era5-002824/windspeed/1-sector.jld2"
    meso_name = "era5-002824"

    [masts.models.winddirection]
    method = "constant-offset"
    model_file = "./meso-models/pn-013945/era5-002824/winddirection/constant-offset.jld2"
    meso_name = "era5-002824"
```

## 智能模型选择

### 1. 性能指标评估
```toml
# 模型选择基于以下指标
[model_selection_criteria]
correlation_weight = 0.4      # 相关系数权重
rmse_weight = 0.3            # RMSE权重
bias_weight = 0.2            # 偏差权重
coverage_weight = 0.1        # 数据覆盖率权重
```
## 重构方法选项

### 1. 线性模型重构
- **16扇区模型**: 精度最高，适用于复杂地形
- **1扇区模型**: 计算简单，适用于均匀地形
- **非线性模型**: 高精度，需要充足训练数据

### 2. 时间序列扩展
- **历史重构**: 1980-2020 长期序列
- **实时重构**: 近期数据填补
- **预测重构**: 短期预测（限制30天内）

### 3. 不确定度量化
- **Bootstrap方法**: 重采样估计不确定度
- **模型集合**: 多模型结果的统计分析
- **置信区间**: 95%置信区间计算

## 自动优化功能

该命令会自动：

1. **模型性能排序**
   - 基于 `train-meso-results.toml` 分析所有训练模型的验证指标
   - 为每个传感器选择最佳模型组合
   - 配置智能的降级路径

2. **参数调优建议**
   - 基于历史表现调整质量阈值
   - 推荐最适合的不确定度估计方法
   - 优化偏差校正参数

3. **质量预测**
   - 估算重构数据的预期质量
   - 识别可能的问题时间段
   - 提供改进建议

## 下一步操作

配置生成后，可以执行以下步骤：

1. **检查配置**: 验证模型选择和重构参数（确保 `train-meso-results.toml` 已生成）
2. **执行重构**: `julia bin/CleanMast.jl process reconstruct-meso ./project/reconstruct-meso.toml`
3. **质量评估**: 检查重构质量和不确定度
4. **生成下一步配置**: `julia bin/CleanMast.jl recommend representative-year ./project`

## 注意事项

- 需要先完成中尺度模型训练，确保 `train-meso-results.toml` 文件存在
- 重构质量直接依赖于模型训练效果和相关性信息
- 长期重构可能需要大量计算时间
- 建议对重构结果进行详细的质量评估
- 超出训练数据范围的外推需要谨慎使用