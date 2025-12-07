# report clean

## 概述

生成数据清理质量报告，分析清理前后的数据状态和质量。

## 语法

```bash
julia bin/CleanMast.jl report clean <项目目录>
```

## 功能

- **传感器清单**: 各测风塔传感器配置
- **数据覆盖率**: 原始数据与清理后数据对比
- **违规分析**: 数据清理规则违规统计
- **质量评估**: 数据完整性和可靠性分析

## 输出文件

```
report-masts/clean/
├── report.typ           # 主报告文件
├── plots/              # 图表文件
└── generation.log      # 生成日志
```

## 配置

使用项目中的 `process-clean.toml` 配置，无需额外配置文件。