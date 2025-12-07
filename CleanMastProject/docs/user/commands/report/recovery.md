# report recovery

## 概述

生成数据恢复状态分析报告，评估各重构阶段的数据恢复效果。

## 语法

```bash
julia bin/CleanMast.jl report recovery <配置文件路径>
```

## 功能

- **恢复统计**: 各阶段数据恢复百分比
- **对比分析**: 重构前后数据覆盖率对比
- **质量评估**: 重构数据质量指标
- **可视化报告**: 恢复效果图表

## 配置文件

### report-recovery.toml
```toml
[[masts]]
name = "M230016"

    [masts.tower_shading]
    sensors = "../tower-shading/M230016.sensors.yaml"
    data = "../tower-shading/M230016.csv"

    [masts.reconstruct_single]
    sensors = "../reconstruct-single/M230016.sensors.yaml"
    data = "../reconstruct-single/M230016.csv"

    [masts.reconstruct_cross]
    sensors = "../reconstruct-cross/M230016_reconstructed.sensors.yaml"
    data = "../reconstruct-cross/M230016_reconstructed.csv"

    [masts.reconstruct_meso]
    sensors = "../reconstruct-meso/M230016.sensors.yaml"
    data = "../reconstruct-meso/M230016.csv"

    [masts.time_range]
    max = 2025-07-31T23:59:59.000Z
    min = 2023-08-01T00:00:00.000Z

[output]
report_dir = "./recovery"
report_filename = "recovery-report.typ"
```

## 输出文件

```
report-masts/recovery/
├── recovery-report.typ    # 主报告文件
└── plots/                # 图表文件
```

## 配置生成

```bash
recommend report-all <项目目录>  # 自动生成配置
```