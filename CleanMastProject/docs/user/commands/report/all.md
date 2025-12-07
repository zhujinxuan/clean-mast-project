# report all

## 概述

生成项目的综合分析报告，包括所有数据处理阶段的报告。

## 语法

```bash
julia bin/CleanMast.jl report all <项目目录>
```

## 功能

自动生成以下 8 个综合报告：

1. **数据清理报告** (`clean/`): 原始数据与清洗后数据对比分析
2. **数据恢复分析** (`recovery/`): 各重构阶段数据覆盖率追踪
3. **单塔重构报告** (`reconstruct-single/`): 单塔重构前后对比分析
4. **跨塔关联分析** (`cross-mast/`): 测风塔间相关性分析
5. **代表年报告** (`representative-year/`): 校准分析
6. **时间序列分析-中尺度** (`timeseries-meso/`): 中尺度重构数据风资源分析
7. **时间序列分析-代表年** (`timeseries-rep/`): 代表年数据风资源分析
8. **中尺度重构报告** (`reconstruct-meso/`): 中尺度-测风塔重构质量分析

## 输出结构

```
report-masts/
├── clean/
│   └── report.typ
├── recovery/
│   └── recovery-report.typ
├── reconstruct-single/
│   └── reconstruction_analysis_report.typ
├── cross-mast/
│   └── report.typ
├── representative-year/
│   └── report.typ
├── timeseries-meso/
│   ├── <mast-name>/
│   └── ...
├── timeseries-rep/
│   ├── <mast-name>/
│   └── ...
└── reconstruct-meso/
    └── report.typ
```

## 前置条件

- 完成数据处理流程 (`process steps --all`)
- 运行 `recommend report-all` 生成配置文件