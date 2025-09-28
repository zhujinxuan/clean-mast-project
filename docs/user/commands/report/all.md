# report all

## 概述

生成项目的综合分析报告，包括所有数据处理阶段的报告。

## 语法

```bash
julia bin/CleanMast.jl report all <项目目录>
```

## 功能

自动生成以下报告：
- **数据清理报告**: 数据质量分析
- **数据恢复分析**: 重构阶段数据恢复统计
- **跨塔关联分析**: 测风塔间相关性分析
- **单塔重构分析**: 单塔重构质量评估
- **时间序列分析**: 中尺度和代表年数据分析

## 输出结构

```
report-masts/
├── clean/report.typ
├── recovery/recovery-report.typ
├── cross-mast/report.typ
├── reconstruct-single/report.yaml
├── timeseries-meso/comprehensive_analysis_report.typ
└── timeseries-rep/comprehensive_analysis_report.typ
```

## 前置条件

- 完成数据处理流程 (`process steps --all`)
- 运行 `recommend report-all` 生成配置文件