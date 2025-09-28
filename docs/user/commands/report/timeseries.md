# report timeseries

## 概述

生成综合风能时间序列分析报告。

## 语法

```bash
julia bin/CleanMast.jl report timeseries <配置文件路径>
```

## 功能

- **风资源评估**: 威布尔分布、年平均风速、风向玫瑰图
- **垂直风切变**: 风切变指数计算和高度外推
- **湍流分析**: 湍流强度、阵风因子
- **极值分析**: 50年一遇极值风速
- **时间特征**: 日变化、月变化、季节变化

## 配置文件

### report-timeseries-meso.toml
```toml
[[masts]]
name = "pn-002824"
[masts.input]
data = "../reconstruct-meso/pn-002824.csv"
sensors = "../reconstruct-meso/pn-002824.sensors.yaml"
[masts.airDensity]
density = 1.225

[output]
path = "timeseries-meso"
```

### report-timeseries-rep.toml
```toml
[[masts]]
name = "pn-002824"
[masts.input]
data = "../representative-year/pn-002824.csv"
sensors = "../representative-year/pn-002824.sensors.yaml"
[masts.airDensity]
density = 1.225

[output]
path = "timeseries-rep"
```

## 输出文件

```
report-masts/timeseries-*/
├── comprehensive_analysis_report.typ  # 主报告
├── {mast_name}/
│   ├── wind-temporal/wind-temporal.typ
│   ├── wind-rose/wind-rose.typ
│   ├── vertical-profile/wind_shear_exponent.typ
│   ├── weibull/weibull.typ
│   └── turbulence/turbulence.typ
└── data/  # CSV数据
```

## 配置生成

```bash
recommend report-all <项目目录>  # 生成两个配置文件
```