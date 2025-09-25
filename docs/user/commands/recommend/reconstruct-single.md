# recommend reconstruct-single

## 概述

生成单测风塔重构的配置文件，利用同一测风塔不同高度传感器间的相关性来填补数据缺失。

## 语法

```bash
julia bin/CleanMast.jl recommend reconstruct-single <项目目录>
```

## 实现位置

**核心实现**: `src/ReconstructSingleMast/RecommendReconstructSingleCommand.jl`

## 功能流程

1. **依赖检查**
   - 读取 `tower-shading.toml` 配置
   - 验证塔影校正后的数据文件
   - 分析传感器高度配置

2. **相关性分析**
   - 计算不同高度传感器间的相关性
   - 识别最佳参考传感器组合
   - 评估数据重构的可行性

3. **配置生成**
   - 创建单测风塔重构条目
   - 设置适当的输入输出路径
   - 配置重构参数和方法

4. **输出文件**
   - 生成 `reconstruct-single.toml` 配置文件

## 相关文件

- **配置文件**: reconstruct-single.toml (待创建配置文档)
- **处理命令**: [process reconstruct-single](../process/reconstruct-single.md)
- **配置类型**: `src/Types/ReconstructSingleConfig.jl`
- **技术实现**: [单测风塔重构算法](../../../technical/algorithms/reconstruct-single.md)

## 输出配置示例

```toml
# reconstruct-single.toml
# 基于实际项目结构: projects/pn-3masts/reconstruct-single.toml
# 使用同一测风塔传感器间相关性填补缺失数据

[[masts]]
name = "测风塔01"

    [masts.input]
    data = "./tower-shading/测风塔01.csv"
    sensors = "./tower-shading/测风塔01.sensors.yaml"

    [masts.output]
    data = "./reconstruct-single/测风塔01.csv"
    sensors = "./reconstruct-single/测风塔01.sensors.yaml"

[[masts]]
name = "测风塔02"

    [masts.input]
    data = "./tower-shading/测风塔02.csv"
    sensors = "./tower-shading/测风塔02.sensors.yaml"

    [masts.output]
    data = "./reconstruct-single/测风塔02.csv"
    sensors = "./reconstruct-single/测风塔02.sensors.yaml"
```

## 重构方法选项

### 1. 线性回归 (linear_regression)
- **适用场景**: 高相关性 (r > 0.9)，大量数据 (> 2000点)
- **精度预期**: RMSE < 0.5 m/s (风速), < 10° (风向)
- **参数**: 最小相关系数、最小数据点数

### 2. 分段线性回归 (segmented_regression)
- **适用场景**: 中等相关性 (r > 0.85)，数据分布不均匀
- **精度预期**: RMSE < 0.4 m/s (风速), < 8° (风向)
- **参数**: 风速分段点、各段最小数据量

### 3. 物理约束回归 (physics_constrained)
- **适用场景**: 大高度差 (> 50m)，需要物理一致性
- **精度预期**: RMSE < 0.6 m/s (风速), < 12° (风向)
- **参数**: 风切变指数范围、截距约束

### 4. 多传感器融合 (multi_reference)
- **适用场景**: 多个参考传感器可用
- **精度预期**: RMSE < 0.3 m/s (风速), < 6° (风向)
- **参数**: 权重分配方法、融合策略

## 自动优化功能

该命令会自动进行：

1. **传感器配对分析**
   - 计算所有传感器对的相关性矩阵
   - 识别最佳重构路径
   - 评估重构质量预期

2. **方法选择建议**
   - 基于数据特征推荐最适合的重构方法
   - 设置合适的参数范围
   - 配置质量控制阈值

3. **性能预测**
   - 估算重构精度指标
   - 预测数据完整性提升
   - 计算置信区间

## 下一步操作

配置生成后，可以执行以下步骤：

1. **检查配置**: 验证重构参数和传感器配对
2. **执行重构**: `julia bin/CleanMast.jl process reconstruct-single ./project/reconstruct-single.toml`
3. **质量评估**: `julia bin/CleanMast.jl analyze reconstruct-single ./project`
4. **生成下一步配置**: `julia bin/CleanMast.jl recommend train-meso ./project`

## 注意事项

- 需要先完成塔影校正步骤
- 重构质量依赖于传感器间的相关性
- 可根据重构效果调整方法和参数
- 建议对重构结果进行质量评估