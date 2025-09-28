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
name = "pn-002824"
[masts.raw]
data = "./clean/pn-002824.csv"
sensors = "./clean/pn-002824.sensors.yaml"
[masts.final]
data = "./reconstruct-meso/pn-002824.csv"
sensors = "./reconstruct-meso/pn-002824.sensors.yaml"

[output]
report_dir = "./report-masts/recovery"
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