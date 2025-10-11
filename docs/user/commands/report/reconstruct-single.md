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
```yaml
masts:
  - name: "M230016"
    before_reconstruction:
      csv: "../tower-shading/M230016.csv"
      sensorConfig: "../tower-shading/M230016.sensors.yaml"
    after_reconstruction:
      csv: "../reconstruct-single/M230016.csv"
      sensorConfig: "../reconstruct-single/M230016.sensors.yaml"

output:
  dir: "./reconstruct-single"
```

## 输出文件

```
report-masts/reconstruct-single/
├── report.yaml          # 主报告文件
└── plots/              # 分析图表
```

## 配置生成

```bash
recommend report-all <项目目录>  # 自动生成配置
```