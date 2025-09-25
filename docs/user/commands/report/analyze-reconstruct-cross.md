# analyze reconstruct-cross

## 概述

分析跨测风塔重构的效果和质量，评估跨塔模型的性能，提供多测风塔间的一致性检查。

## 语法

```bash
julia bin/CleanMast.jl analyze reconstruct-cross <配置文件路径>
```

## 实现位置

**核心实现**: `src/AnalyzeReconstructCross/CommandAnalyzeReconstructCross.jl`
**分析核心**: `src/AnalyzeReconstructCross/AnalysisCore.jl`
**报告生成**: `src/AnalyzeReconstructCross/ReportGeneration.jl`

## 前置条件

- 必须先完成 `process train-reconstruct-cross` 步骤
- 必须先完成 `process reconstruct-cross` 步骤
- 存在跨塔重构的结果数据
- 存在跨塔模型训练结果

## 功能详述

### 1. 跨塔相关性分析

#### 测风塔间相关性
- **距离相关性**: 测风塔间距离与相关性的关系
- **地形影响**: 地形复杂度对相关性的影响
- **高度相关性**: 不同高度间的相关性变化
- **方向性影响**: 风向对跨塔相关性的影响

#### 时间稳定性
- **季节变化**: 跨塔相关性的季节性变化
- **长期趋势**: 相关性的长期稳定性
- **气象条件**: 不同气象条件下的相关性
- **稳定性指标**: 相关性稳定性的量化指标

### 2. 重构模型评估

#### 模型性能指标
- **相关系数**: 重构值与实测值的相关性
- **均方根误差**: 重构精度的量化评估
- **偏差分析**: 系统性偏差的识别和量化
- **不确定度**: 重构结果的不确定度评估

#### 模型适用性
- **适用条件**: 模型的适用气象条件
- **精度区间**: 不同条件下的精度变化
- **可靠性评估**: 模型预测的可靠性
- **外推能力**: 模型的外推预测能力

#### 模型对比
- **多模型比较**: 不同跨塔模型的性能对比
- **最优模型选择**: 基于性能指标的模型选择
- **组合模型**: 多模型融合的效果评估
- **降级策略**: 模型失效时的降级策略评估

### 3. 空间插值质量

#### 插值方法评估
- **克里金插值**: 克里金方法的插值精度
- **反距离权重**: IDW方法的插值效果
- **多项式拟合**: 多项式插值的适用性
- **神经网络**: 机器学习方法的插值性能

#### 空间一致性
- **梯度检查**: 空间风速梯度的合理性
- **连续性验证**: 空间分布的连续性检查
- **物理约束**: 插值结果的物理合理性
- **边界效应**: 边界区域的插值质量

### 4. 多测风塔一致性检查

#### 数据一致性
- **同步性检查**: 多塔数据的时间同步性
- **量级一致性**: 测量值量级的一致性检查
- **变化趋势**: 多塔数据变化趋势的一致性
- **异常识别**: 单塔异常数据的识别

#### 重构一致性
- **重构效果**: 各塔重构效果的一致性
- **质量分布**: 重构质量在空间上的分布
- **可靠性**: 重构结果的整体可靠性
- **互验证**: 多塔间的交叉验证

## 配置文件格式

### YAML配置示例
```yaml
# 跨塔重构分析配置
# 位置: report-masts/analyze-reconstruct-cross.toml

cross_reconstruction:
  training_results: "./train-reconstruct-cross/train-results.toml"
  reconstruction_config: "./reconstruct-cross.toml"

masts:
  - name: "pn-002824"
    original_data:
      csv: "./reconstruct-single/pn-002824.csv"
      sensors: "./reconstruct-single/pn-002824.sensors.yaml"
    reconstructed_data:
      csv: "./reconstruct-cross/pn-002824_reconstructed.csv"
      sensors: "./reconstruct-cross/pn-002824_reconstructed.sensors.yaml"
    location:
      longitude: 116.3
      latitude: 39.9
      elevation: 50.0

  - name: "pn-013945"
    original_data:
      csv: "./reconstruct-single/pn-013945.csv"
      sensors: "./reconstruct-single/pn-013945.sensors.yaml"
    reconstructed_data:
      csv: "./reconstruct-cross/pn-013945_reconstructed.csv"
      sensors: "./reconstruct-cross/pn-013945_reconstructed.sensors.yaml"
    location:
      longitude: 116.5
      latitude: 40.1
      elevation: 45.0

analysis_options:
  spatial_interpolation: true
  correlation_analysis: true
  model_performance: true
  uncertainty_quantification: true

output:
  dir: "./report-masts/reconstruct-cross"
  generate_maps: true
  include_detailed_statistics: true
```

## 输出文件结构

```
report-masts/reconstruct-cross/
├── cross-reconstruction-report.pdf       # 综合分析报告
├── model-performance/
│   ├── correlation-analysis.csv          # 相关性分析结果
│   ├── rmse-statistics.csv              # RMSE统计
│   ├── bias-analysis.csv                # 偏差分析
│   └── model-comparison.csv             # 模型对比
├── spatial-analysis/
│   ├── interpolation-quality.csv        # 插值质量评估
│   ├── spatial-consistency.csv          # 空间一致性
│   └── spatial-maps/                    # 空间分布图
├── cross-validation/
│   ├── validation-statistics.csv        # 交叉验证统计
│   ├── reliability-assessment.csv       # 可靠性评估
│   └── uncertainty-analysis.csv         # 不确定度分析
└── consistency-check/
    ├── data-synchronization.csv         # 数据同步性
    ├── trend-consistency.csv            # 趋势一致性
    └── anomaly-detection.csv           # 异常检测结果
```

## 分析方法

### 1. 统计分析方法
- **描述统计**: 基本统计量的计算和比较
- **假设检验**: 统计显著性的检验
- **方差分析**: 多组数据的方差分析
- **时间序列**: 时间序列的统计分析

### 2. 空间分析方法
- **地统计学**: 基于地统计学的空间分析
- **空间自相关**: Moran's I等空间自相关分析
- **变异函数**: 空间变异性的变异函数分析
- **空间插值**: 多种空间插值方法的应用

### 3. 机器学习方法
- **特征工程**: 相关特征的提取和选择
- **模型训练**: 机器学习模型的训练和优化
- **交叉验证**: k折交叉验证的模型评估
- **超参优化**: 超参数的优化和调整

## 质量控制

### 1. 数据质量检查
- **完整性检查**: 数据文件的完整性验证
- **一致性检查**: 多源数据的一致性验证
- **异常值检测**: 自动异常值识别和处理
- **时间对齐**: 多塔数据的时间对齐验证

### 2. 分析质量控制
- **参数验证**: 分析参数的合理性验证
- **结果检验**: 分析结果的物理合理性检验
- **不确定度**: 分析不确定度的评估
- **敏感性**: 关键参数的敏感性分析

## 报告内容

### 1. 综合评估
- **重构效果评估**: 跨塔重构的整体效果评估
- **模型性能排序**: 不同模型的性能排序
- **最佳实践**: 基于分析的最佳实践建议
- **改进方向**: 进一步改进的方向建议

### 2. 详细分析
- **统计分析表**: 详细的统计分析结果表格
- **性能指标图**: 模型性能的可视化展示
- **空间分布图**: 重构质量的空间分布
- **时间序列图**: 重构效果的时间变化

### 3. 技术附录
- **方法描述**: 分析方法的详细描述
- **参数设置**: 分析参数的设置说明
- **数据说明**: 输入数据的详细说明
- **引用文献**: 相关技术文献引用

## 相关文件

- **配置生成**: [recommend report-all](../recommend/report-all.md)
- **跨塔训练**: [process train-reconstruct-cross](../process/train-reconstruct-cross.md)
- **跨塔重构**: [process reconstruct-cross](../process/reconstruct-cross.md)
- **配置类型**: `src/Types/AnalyzeReconstructCrossConfig.jl`

## 应用场景

- **跨塔重构验证**: 验证跨塔重构的有效性
- **模型优化**: 优化跨塔重构模型
- **风场规划**: 为风电场规划提供技术支持
- **数据质量控制**: 多塔数据的质量控制

## 注意事项

- 需要准确的测风塔地理位置信息
- 确保跨塔训练和重构步骤已完成
- 考虑地形和气象条件对分析结果的影响
- 大型项目的分析可能需要较长时间
- 建议结合实地调研验证分析结果