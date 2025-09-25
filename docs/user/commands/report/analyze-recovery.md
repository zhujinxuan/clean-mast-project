# analyze recovery

## 概述

分析数据恢复率和处理流程的效果，评估从原始数据到最终重构的整个数据恢复过程。

## 语法

```bash
julia bin/CleanMast.jl analyze recovery <配置文件路径>
```

## 实现位置

**核心实现**: `src/ReportRecovery/ReportRecoveryCommand.jl`
**恢复分析**: `src/ReportRecovery/RecoveryAnalysis.jl`
**状态报告**: `src/ReportRecovery/RecoveryStatusReport.jl`

## 前置条件

- 必须完成完整的数据处理流程
- 存在各处理阶段的数据文件
- 配置文件正确指定了各阶段数据路径

## 功能详述

### 1. 数据恢复率分析

#### 阶段性恢复率
分析各处理阶段的数据恢复情况：

- **原始数据** (raw): 传感器原始采集数据的完整性
- **清理数据** (clean): 数据清理后的有效数据比例
- **塔影校正** (tower-shading): 塔影校正对数据量的影响
- **单塔重构** (reconstruct-single): 单塔重构带来的数据恢复
- **中尺度重构** (reconstruct-meso): 中尺度重构的数据补充
- **代表年校准** (representative-year): 最终数据的完整性

#### 累积恢复统计
- **整体恢复率**: 从原始到最终的总体数据恢复率
- **阶段贡献**: 各阶段对总恢复率的贡献
- **恢复效率**: 单位处理成本的数据恢复效益
- **质量权重**: 考虑数据质量的加权恢复率

#### 传感器级恢复
- **风速传感器**: 各高度风速传感器的恢复情况
- **风向传感器**: 各高度风向传感器的恢复情况
- **温度传感器**: 温度测量的数据恢复
- **其他传感器**: 气压、湿度等的恢复统计

### 2. 处理效果评估

#### 数据清理效果
- **异常值移除**: 清理阶段移除的异常值统计
- **质量提升**: 数据质量评分的提升程度
- **一致性改善**: 数据一致性的改善效果
- **可靠性增强**: 数据可靠性的增强程度

#### 重构效果评估
- **重构精度**: 不同重构方法的精度比较
- **覆盖率提升**: 重构带来的数据覆盖率改善
- **时间分布**: 重构数据在时间上的分布
- **空间分布**: 重构效果在不同传感器上的分布

#### 校准效果分析
- **代表性改善**: 代表年校准的代表性改善
- **长期趋势**: 校准对长期趋势的影响
- **统计特征**: 校准前后统计特征的变化
- **不确定度**: 校准引入的不确定度

### 3. 质量演进分析

#### 数据质量指标
- **完整性指标**: 数据完整性的量化评估
- **准确性指标**: 数据准确性的评估方法
- **一致性指标**: 数据一致性的量化方法
- **可靠性指标**: 数据可靠性的评估标准

#### 质量演进轨迹
- **质量提升曲线**: 各阶段数据质量的提升轨迹
- **关键转折点**: 质量显著改善的关键处理步骤
- **瓶颈识别**: 质量提升的瓶颈环节识别
- **优化潜力**: 进一步质量优化的潜力分析

### 4. 成本效益分析

#### 处理成本统计
- **计算成本**: 各处理步骤的计算时间成本
- **存储成本**: 中间数据文件的存储成本
- **人工成本**: 人工干预和配置的成本
- **总体成本**: 完整处理流程的总体成本

#### 效益量化
- **数据价值**: 恢复数据的经济价值评估
- **质量效益**: 数据质量提升带来的效益
- **时间效益**: 处理时间节约带来的效益
- **风险降低**: 数据质量改善降低的风险成本

## 配置文件格式

### TOML配置示例
```toml
# 数据恢复分析配置
# 位置: report-masts/analyze-recovery.toml

[recovery_analysis]
stages = [
    "raw",
    "clean",
    "tower-shading",
    "reconstruct-single",
    "reconstruct-meso",
    "representative-year"
]

[[masts]]
name = "pn-002824"
    [masts.stages.raw]
    data = "./raw/pn-002824.csv"
    sensors = "./raw/pn-002824.sensors.toml"
    [masts.stages.clean]
    data = "./clean/pn-002824.csv"
    sensors = "./clean/pn-002824.sensors.yaml"
    [masts.stages.tower_shading]
    data = "./tower-shading/pn-002824.csv"
    sensors = "./tower-shading/pn-002824.sensors.yaml"
    [masts.stages.reconstruct_single]
    data = "./reconstruct-single/pn-002824.csv"
    sensors = "./reconstruct-single/pn-002824.sensors.yaml"
    [masts.stages.reconstruct_meso]
    data = "./reconstruct-meso/pn-002824.csv"
    sensors = "./reconstruct-meso/pn-002824.sensors.yaml"
    [masts.stages.final]
    data = "./representative-year/pn-002824.csv"
    sensors = "./representative-year/pn-002824.sensors.yaml"

[analysis_options]
include_stage_comparison = true
generate_recovery_statistics = true
calculate_quality_metrics = true
perform_cost_benefit_analysis = true

[output]
path = "./report-masts/recovery"
generate_detailed_plots = true
include_recommendations = true
```

## 输出文件结构

```
report-masts/recovery/
├── recovery-analysis-report.pdf          # 综合恢复分析报告
├── recovery-statistics/
│   ├── stage-recovery-rates.csv          # 各阶段恢复率统计
│   ├── cumulative-recovery.csv           # 累积恢复统计
│   ├── sensor-recovery-matrix.csv        # 传感器恢复矩阵
│   └── recovery-timeline.csv             # 恢复时间线数据
├── quality-evolution/
│   ├── quality-metrics.csv               # 质量指标演进
│   ├── quality-improvement.csv           # 质量改善统计
│   └── quality-benchmarks.csv            # 质量基准对比
├── cost-benefit/
│   ├── processing-costs.csv              # 处理成本统计
│   ├── benefit-quantification.csv        # 效益量化分析
│   └── cost-effectiveness.csv            # 成本效益分析
└── visualizations/
    ├── recovery-flow-diagram.png         # 恢复流程图
    ├── quality-evolution-chart.png       # 质量演进图
    ├── cost-benefit-analysis.png         # 成本效益图
    └── recovery-heatmap.png              # 恢复效果热图
```

## 分析方法

### 1. 恢复率计算
- **简单恢复率**: 有效数据点 / 总时间点
- **加权恢复率**: 考虑数据重要性的加权恢复率
- **质量调整恢复率**: 考虑数据质量的调整恢复率
- **时间段恢复率**: 不同时间段的恢复率对比

### 2. 质量评估方法
- **多维质量评分**: 综合多个质量维度的评分
- **质量改善指数**: 质量改善程度的量化指数
- **基准对比**: 与行业标准的对比分析
- **趋势分析**: 质量演进的趋势分析

### 3. 统计分析
- **描述统计**: 恢复率的基本统计量
- **相关分析**: 不同因素与恢复效果的相关性
- **回归分析**: 恢复效果的影响因素分析
- **方差分析**: 不同条件下恢复效果的差异

## 质量控制

### 1. 数据验证
- **文件存在性**: 验证各阶段数据文件存在
- **格式一致性**: 检查数据格式的一致性
- **时间对齐**: 确保各阶段数据时间对齐
- **传感器匹配**: 验证传感器配置匹配

### 2. 分析验证
- **计算准确性**: 验证恢复率计算的准确性
- **逻辑一致性**: 检查分析逻辑的一致性
- **结果合理性**: 验证分析结果的合理性
- **不确定度**: 评估分析结果的不确定度

## 报告内容

### 1. 执行摘要
- **整体恢复效果**: 数据恢复的总体效果评估
- **关键成就**: 数据处理的关键成就
- **主要发现**: 分析的主要发现和洞察
- **建议**: 基于分析的改进建议

### 2. 详细统计
- **阶段性统计**: 各处理阶段的详细统计
- **传感器统计**: 各传感器的恢复统计
- **时间序列**: 恢复效果的时间序列分析
- **对比分析**: 不同条件下的对比分析

### 3. 可视化展示
- **恢复流程图**: 数据恢复的流程可视化
- **质量演进图**: 数据质量的演进过程
- **对比图表**: 各阶段效果的对比图表
- **热图分析**: 恢复效果的热图展示

## 相关文件

- **配置生成**: [recommend report-all](../recommend/report-all.md)
- **配置类型**: `src/Types/ReportRecoveryConfig.jl`

## 应用场景

- **质量评估**: 评估数据处理流程的质量效果
- **流程优化**: 优化数据处理流程和参数
- **成本控制**: 控制数据处理的成本
- **技术报告**: 为技术报告提供恢复分析

## 注意事项

- 确保各阶段数据文件完整存在
- 注意处理不同阶段的数据格式差异
- 考虑处理步骤对数据质量的复合影响
- 恢复率分析需要考虑数据的重要性权重
- 建议定期评估和优化数据处理流程