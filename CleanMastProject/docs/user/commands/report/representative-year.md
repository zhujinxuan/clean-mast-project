# report representative-year

## 概述

生成代表年校正分析报告，评估气候学校正效果和代表年选择质量。

## 语法

```bash
julia bin/CleanMast.jl report representative-year <项目目录>
```

## 功能

- **气候学分析**: 气候学与训练期数据对比
- **变化率计算**: 训练期和代表年相对气候学的变化百分比
- **扇区分析**: 16方向扇区详细分析
- **传感器校正**: 传感器级别的校正状态
- **校正效果**: 代表年校正质量评估

## 输出文件

```
report-masts/representative-year/
├── report.typ                           # 主报告
├── tables/
│   ├── {mast}_{meso}_sectors.typ       # 扇区分析表
│   └── {mast}_{meso}_sensors.typ       # 传感器分析表
└── data/
    ├── calibration_summary.csv         # 校正汇总
    └── sector_analysis.csv            # 扇区详细数据
```

## 配置

使用项目中的 `representative-year.toml` 配置，无需额外配置文件。