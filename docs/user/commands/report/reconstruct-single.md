# report reconstruct-single

## 概述

生成单测风塔重构质量分析报告，评估基于相关性的数据重构效果。

## 语法

```bash
julia bin/CleanMast.jl report reconstruct-single <配置文件路径>
```

## 功能

- **重构效果**: 单塔重构前后数据对比
- **相关性分析**: 重构模型质量评估
- **数据覆盖**: 重构数据完整性统计
- **质量指标**: 重构精度和可靠性评估

## 配置文件

### report-reconstruct-single.yaml

使用 `TimeSeriesSource` 格式配置重构前后数据：

```yaml
masts:
  - name: "M230016"
    before_reconstruction:
      input:
        data: "../tower-shading/M230016.csv"
        sensors: "../tower-shading/M230016.sensors.yaml"
    after_reconstruction:
      input:
        data: "../reconstruct-single/M230016.csv"
        sensors: "../reconstruct-single/M230016.sensors.yaml"

output:
  dir: "./reconstruct-single"
```

### 配置说明

- `input.data`: 时间序列数据文件路径（CSV 格式）
- `input.sensors`: 传感器配置文件路径（YAML 格式）
- 支持相对路径和绝对路径
- 路径相对于配置文件所在目录解析

## 输出文件

```
report-masts/reconstruct-single/
├── reconstruction_analysis_report.typ  # 主报告文件（Typst 格式）
├── correlation_plots/                  # 相关性分析图表
│   ├── correlation_high_vs_high.png
│   ├── correlation_high_vs_low.png
│   └── correlation_low_vs_low.png
└── wind_speed_r2_matrix.csv           # R²相关系数矩阵
```

### 报告内容

1. **数据覆盖率分析**: 重构前后数据完整性统计
2. **风速相关性分析**: 不同高度间风速相关性（R²矩阵）
3. **风向差异分析**: 不同高度间风向差异统计

### 高度传感器分组规则

报告自动将传感器分为"高层"和"低层"：
- 如果有 3 个及以上高度 ≥100m 的传感器，则这些传感器为高层
- 否则，取最高的 3 个传感器作为高层
- 其余传感器为低层

## 配置生成

```bash
recommend report-all <项目目录>  # 自动生成配置
```