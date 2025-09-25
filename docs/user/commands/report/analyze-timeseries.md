# analyze timeseries

## 概述

执行综合风能时间序列分析和报告生成，提供详细的风资源评估和统计分析。

## 语法

```bash
julia bin/CleanMast.jl analyze timeseries <配置文件路径>
```

## 实现位置

**核心实现**: `src/AnalyzeTimeSeries.jl`
**湍流分析**: `src/AnalyzeTimeSeries/Turbulence.jl`
**风时程分析**: `src/AnalyzeTimeSeries/WindTemporal.jl`

## 前置条件

- 存在相应的时间序列分析配置文件
- 输入数据文件必须存在且格式正确
- 传感器配置文件与数据文件匹配

## 功能详述

### 1. 风资源评估
- **风速分布分析**: 威布尔分布拟合、形状参数和尺度参数
- **风向分析**: 风向玫瑰图、主导风向识别
- **风功率密度**: 不同高度的风功率密度计算
- **年平均风速**: 各高度年平均风速统计

### 2. 湍流特性分析
- **湍流强度**: 标准化湍流强度计算
- **阵风因子**: 阵风与平均风速比值
- **湍流谱分析**: 功率谱密度分析
- **相干性分析**: 不同高度间的相干性

### 3. 垂直风切变
- **风切变指数**: 风切变指数α的计算
- **高度外推**: 基于切变指数的风速外推
- **稳定性分析**: 大气稳定性对切变的影响

### 4. 极值分析
- **极值风速**: 年极值、月极值统计
- **重现期分析**: 不同重现期的极值风速
- **概率分布**: 极值分布的统计特征

### 5. 时间变化特征
- **月变化**: 月平均风速和风向变化
- **日变化**: 日平均和小时变化模式
- **季节性**: 季节性风资源变化特征

## 配置文件格式

### 基于 report-masts/ 的标准配置
```toml
# 时间序列分析配置
# 位置: report-masts/analyze-*.toml

[[masts]]
name = "pn-002824"
    [masts.input]
    data = "./reconstruct-meso/pn-002824.csv"
    sensors = "./reconstruct-meso/pn-002824.sensors.yaml"
    [masts.airDensity]
    density = 1.225  # kg/m³ at sea level, 15°C
    reference_height = 10.0

[[masts]]
name = "pn-013945"
    [masts.input]
    data = "./reconstruct-meso/pn-013945.csv"
    sensors = "./reconstruct-meso/pn-013945.sensors.yaml"
    [masts.airDensity]
    density = 1.225
    reference_height = 10.0

[output]
path = "./report-masts/reconstruct-meso"
report_format = ["pdf", "html"]
include_uncertainty = true
```

### 配置参数说明
- **masts.input**: 输入数据和传感器配置文件路径
- **airDensity**: 空气密度参数，用于功率计算
- **reference_height**: 参考高度，用于风切变分析
- **output.path**: 报告输出目录
- **report_format**: 报告格式选项（pdf, html, csv）

## 输出文件结构

```
report-masts/{analysis-type}/
├── report.html                 # 交互式网页报告
├── report.pdf                  # PDF技术报告
├── data/
│   ├── wind-statistics.csv     # 风统计数据
│   ├── turbulence-analysis.csv # 湍流分析结果
│   └── extreme-analysis.csv    # 极值分析数据
└── figures/
    ├── wind-rose.png           # 风向玫瑰图
    ├── weibull-fit.png         # 威布尔分布拟合
    ├── turbulence-profile.png  # 湍流强度廓线
    └── time-series.png         # 时间序列图
```

## 报告内容

### 1. HTML交互式报告
- **动态图表**: 可交互的风向玫瑰图、时间序列图
- **数据筛选**: 按时间、风速、风向筛选数据
- **统计汇总**: 实时统计信息更新
- **导出功能**: 图表和数据导出

### 2. PDF技术报告
- **执行摘要**: 关键统计指标汇总
- **详细分析**: 各类分析的详细结果
- **专业图表**: 高质量的技术图表
- **数据表格**: 完整的统计数据表

### 3. 数据文件
- **CSV格式**: 所有统计结果的原始数据
- **标准化格式**: 便于后续分析和处理
- **元数据**: 包含分析参数和配置信息

## 技术特点

### 1. 数据处理
- **自动质量检查**: 异常值识别和处理
- **时间对齐**: 时间序列规律化处理
- **缺失值处理**: 智能缺失数据处理策略
- **单位转换**: 自动单位识别和转换

### 2. 统计方法
- **参数估计**: 最大似然估计、矩估计
- **假设检验**: 分布拟合度检验
- **置信区间**: 统计参数的置信区间
- **不确定度**: 测量和统计不确定度

### 3. 可视化
- **科学制图**: 符合科学出版标准的图表
- **色彩管理**: 色盲友好的配色方案
- **中文支持**: 完整的中文标签和说明
- **矢量输出**: 高质量矢量图输出

## 相关文件

- **配置生成**: [recommend report-all](../recommend/report-all.md)
- **配置类型**: `src/Types/AnalyzeTimeSeriesConfig.jl`

## 应用场景

### 1. 风电项目评估
- 风电场选址的风资源评估
- 风机类型选择的技术支持
- 发电量评估的基础数据

### 2. 工程设计
- 风荷载设计参数确定
- 结构安全评估
- 疲劳载荷分析

### 3. 科学研究
- 风特性研究
- 大气边界层研究
- 气候变化影响评估

## 注意事项

- 确保输入数据的质量和完整性
- 根据项目特点调整分析参数
- 检查传感器配置的准确性
- 分析结果需要结合实际情况解读
- 大数据集分析可能需要较长时间
- 建议定期备份分析结果