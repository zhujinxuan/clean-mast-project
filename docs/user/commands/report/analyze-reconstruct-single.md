# analyze reconstruct-single

## 概述

评估单测风塔重构的效果和质量，比较重构前后的数据，提供重构质量的详细分析。

## 语法

```bash
julia bin/CleanMast.jl analyze reconstruct-single <配置文件路径>
```

## 实现位置

**核心实现**: `src/AnalyzeReconstructSingle.jl`
**数据覆盖**: `src/AnalyzeReconstructSingle/DataCoverage.jl`
**风速相关性**: `src/AnalyzeReconstructSingle/WindSpeedCorrelation.jl`
**风向差异**: `src/AnalyzeReconstructSingle/WindDirectionDifference.jl`
**报告生成**: `src/AnalyzeReconstructSingle/ReportGeneration.jl`

## 前置条件

- 必须先完成 `process reconstruct-single` 步骤
- 存在重构前和重构后的数据文件
- 配置文件正确指定了重构前后的数据路径

## 功能详述

### 1. 数据覆盖分析

#### 缺失数据统计
- **重构前统计**: 各传感器原始缺失数据点数量
- **重构后统计**: 各传感器重构后缺失数据点数量
- **缺失率计算**: 缺失数据占总数据的百分比
- **覆盖率提升**: 重构带来的数据覆盖率改善

#### 分传感器分析
- **风速传感器**: 各高度风速传感器的独立统计
- **风向传感器**: 各高度风向传感器的独立统计
- **温度传感器**: 温度测量的覆盖率分析
- **其他传感器**: 气压、湿度等其他测量的统计

#### 时间分布分析
- **月度分布**: 缺失数据的月度分布特征
- **季节性**: 缺失数据的季节性模式
- **连续性**: 缺失数据的连续性特征
- **重构成功率**: 不同时段的重构成功率

### 2. 风速相关性分析

#### 相关系数矩阵
- **R²矩阵**: 所有高度对之间的决定系数矩阵
- **Pearson相关**: 线性相关系数分析
- **Spearman相关**: 等级相关分析
- **显著性检验**: 相关性的统计显著性

#### 回归分析
- **线性回归**: 高度对之间的线性回归分析
- **回归参数**: 斜率、截距、标准误差
- **残差分析**: 回归残差的分布和特征
- **预测区间**: 回归预测的置信区间

#### 分组分析
按高度范围分组的详细分析：
- **高高相关** (≥100m vs ≥100m): 高海拔传感器间相关性
- **高低相关** (≥100m vs <100m): 高低海拔传感器间相关性
- **低低相关** (<100m vs <100m): 低海拔传感器间相关性

#### 可视化分析
- **散点图**: 传感器对之间的散点图
- **回归线**: 线性回归拟合线
- **置信带**: 回归预测的置信带
- **相关性热图**: 相关系数的热图可视化

### 3. 风向差异分析

#### 风向偏差统计
- **平均偏差**: 高度对之间的平均风向差异
- **标准偏差**: 风向差异的变异性
- **偏差范围**: 风向差异的最大和最小值
- **异常检测**: 异常风向偏差的识别

#### 圆形统计
- **圆形平均**: 考虑0°/360°环绕的圆形平均
- **圆形方差**: 风向散布的圆形方差
- **方向统计**: 主导方向和散布程度
- **von Mises拟合**: von Mises分布拟合

#### 分布分析
- **偏差分布**: 风向偏差的分布特征
- **频率分析**: 不同偏差区间的频率
- **概率密度**: 偏差的概率密度函数
- **累积分布**: 偏差的累积分布函数

### 4. 重构质量评估

#### 精度指标
- **均方根误差**: 重构值与参考值的RMSE
- **平均绝对误差**: 重构值的平均绝对误差
- **相对误差**: 重构值的相对误差统计
- **偏差**: 系统性偏差的评估

#### 一致性检验
- **时间一致性**: 重构数据的时间连续性
- **物理一致性**: 重构值的物理合理性
- **统计一致性**: 重构前后的统计特征对比
- **极值一致性**: 极值的合理性检验

## 配置文件格式

### YAML配置示例
```yaml
# 单塔重构分析配置
# 位置: report-masts/analyze-reconstruct-single.toml

masts:
  - name: "pn-002824"
    before_reconstruction:
      csv: "./tower-shading/pn-002824.csv"
      sensorConfig: "./tower-shading/pn-002824.sensors.yaml"
    after_reconstruction:
      csv: "./reconstruct-single/pn-002824.csv"
      sensorConfig: "./reconstruct-single/pn-002824.sensors.yaml"

  - name: "pn-013945"
    before_reconstruction:
      csv: "./tower-shading/pn-013945.csv"
      sensorConfig: "./tower-shading/pn-013945.sensors.yaml"
    after_reconstruction:
      csv: "./reconstruct-single/pn-013945.csv"
      sensorConfig: "./reconstruct-single/pn-013945.sensors.yaml"

output:
  dir: "./report-masts/reconstruct-single"
  generate_detailed_plots: true
  include_statistics: true
```

## 输出文件结构

```
report-masts/reconstruct-single/
├── reconstruction_analysis_report.typ    # Typst格式综合报告
├── reconstruction_analysis_report.pdf    # PDF格式报告
├── data-coverage/
│   ├── coverage-statistics.csv           # 数据覆盖统计
│   └── missing-data-analysis.csv         # 缺失数据分析
├── correlation-analysis/
│   ├── correlation-matrix.csv            # 相关系数矩阵
│   ├── regression-parameters.csv         # 回归参数
│   └── scatter-plots/                    # 散点图集合
└── wind-direction/
    ├── direction-differences.csv         # 风向差异统计
    ├── direction-statistics.csv          # 风向统计分析
    └── direction-plots/                  # 风向分析图表
```

## 数据处理特点

### 1. 时间序列处理
- **10分钟间隔**: 时间序列规律化为标准10分钟间隔
- **时间对齐**: 重构前后数据的精确时间对齐
- **缺失值处理**: 缺失时间戳填充为缺失值标记
- **重叠分析**: 仅分析重构前后的重叠时间范围

### 2. 统计计算
- **缺失值跳过**: 统计计算时正确跳过缺失值
- **有效数据**: 基于有效数据点进行统计分析
- **置信区间**: 统计参数的置信区间计算
- **显著性检验**: 统计结果的显著性评估

### 3. 质量控制
- **异常值检测**: 自动识别和标记异常值
- **数据验证**: 输入数据的完整性验证
- **一致性检查**: 传感器配置与数据的一致性
- **结果验证**: 分析结果的合理性检验

## 报告内容

### 1. 执行摘要
- **重构效果概述**: 重构带来的整体改善
- **关键指标**: 数据覆盖率、相关性等关键指标
- **质量评估**: 重构质量的总体评估
- **建议**: 基于分析结果的改进建议

### 2. 详细分析表格
- **数据覆盖表**: 各传感器的详细覆盖统计
- **相关性表**: 相关系数和回归参数表
- **风向差异表**: 风向偏差的统计表格
- **质量指标表**: 重构质量的量化指标

### 3. 可视化图表
- **覆盖率对比**: 重构前后覆盖率对比图
- **相关性热图**: 传感器间相关性热图
- **散点图矩阵**: 高度对的散点图矩阵
- **风向差异分布**: 风向偏差的分布图

## 相关文件

- **配置生成**: [recommend report-all](../recommend/report-all.md)
- **配置类型**: `src/Types/AnalyzeReconstructSingleConfig.jl`

## 应用场景

- **重构质量验证**: 验证单塔重构的效果
- **模型性能评估**: 评估重构模型的性能
- **数据质量控制**: 控制重构数据的质量
- **技术报告**: 为技术报告提供量化分析

## 注意事项

- 确保重构前后数据文件格式一致
- 检查传感器配置的准确性和一致性
- 注意处理风向的圆形特性
- 大数据集分析可能需要较长时间
- 建议定期验证重构质量