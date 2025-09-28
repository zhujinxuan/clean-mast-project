# 报告配置文件

## 概述

报告配置文件用于生成各类分析报告，由 `recommend report-all` 命令自动生成。

## 配置文件结构

```
report-masts/
├── report-timeseries-meso.toml       # 中尺度重构数据时间序列分析
├── report-timeseries-rep.toml        # 代表年数据时间序列分析
├── report-recovery.toml              # 数据恢复率分析
├── report-cross-mast.toml            # 跨塔相关性分析
└── report-reconstruct-single.yaml    # 单塔重构质量分析
```

## 时间序列分析配置

### report-timeseries-meso.toml
```toml
[[masts]]
name = "pn-002824"
[masts.input]
data = "../reconstruct-meso/pn-002824.csv"
sensors = "../reconstruct-meso/pn-002824.sensors.yaml"
[masts.airDensity]
density = 1.225
reference_height = 10.0

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
reference_height = 10.0

[output]
path = "timeseries-rep"
```

## 数据恢复分析配置

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

## 跨塔分析配置

### report-cross-mast.toml
```toml
[[mast_pairs]]
reference_mast = "pn-002824"
target_mast = "pn-013945"
[mast_pairs.data]
reference_data = "./reconstruct-single/pn-002824.csv"
target_data = "./reconstruct-single/pn-013945.csv"

[output]
report_dir = "./report-masts/cross-mast"
report_filename = "report.typ"
```

## 单塔重构分析配置

### report-reconstruct-single.yaml
```yaml
masts:
  - name: "pn-002824"
    raw_data: "./clean/pn-002824.csv"
    reconstructed_data: "./reconstruct-single/pn-002824.csv"
    sensors: "./reconstruct-single/pn-002824.sensors.yaml"

output:
  report_dir: "./report-masts/reconstruct-single"
  report_filename: "report.yaml"
```

## 配置生成

所有报告配置文件都由以下命令自动生成：

```bash
julia bin/CleanMast.jl recommend report-all <项目目录>
```

## 注意事项

- 路径使用相对路径，相对于项目根目录
- 配置文件生成前需要完成相应的数据处理步骤
- 手动修改配置文件时注意保持路径正确性