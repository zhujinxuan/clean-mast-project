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

## 路径相对性说明

报告配置文件使用**配置文件相对路径**，而非项目相对路径：

- **配置文件位置**：`report-masts/report-xxx.toml`
- **输入数据路径**：相对于 `report-masts/` 目录
  - 示例：`../reconstruct-meso/...` （向上一级到项目根目录）
- **输出目录路径**：相对于 `report-masts/` 目录
  - 示例：`./recovery` （在 report-masts/ 下创建 recovery/）

这种设计使配置文件具有位置独立性，可以随配置文件移动而自动调整路径。

## 时间序列分析配置

### report-timeseries-meso.toml
```toml
[[masts]]
name = "M230016"
[masts.input]
data = "../reconstruct-meso/M230016.csv"
sensors = "../reconstruct-meso/M230016.sensors.yaml"

[output]
path = "timeseries-meso"
```

### report-timeseries-rep.toml
```toml
[[masts]]
name = "M230016"
[masts.input]
data = "../representative-year/M230016.csv"
sensors = "../representative-year/M230016.sensors.yaml"

[output]
path = "timeseries-rep"
```

## 数据恢复分析配置

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

## 跨塔分析配置

### report-cross-mast.toml
```toml
[[masts]]
name = "M230016"
    [masts.input]
    sensors = "../reconstruct-single/M230016.sensors.yaml"
    data = "../reconstruct-single/M230016.csv"

[[masts]]
name = "M230015"
    [masts.input]
    sensors = "../reconstruct-single/M230015.sensors.yaml"
    data = "../reconstruct-single/M230015.csv"

[analyze]
language = "zh"
output_dir = "./cross-mast"
include_plots = true
```

## 单塔重构分析配置

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

## 配置生成

所有报告配置文件都由以下命令自动生成：

```bash
julia bin/CleanMast.jl recommend report-all <项目目录>
```

## 注意事项

- 路径使用相对路径，相对于配置文件所在目录（`report-masts/`）
- 配置文件生成前需要完成相应的数据处理步骤
- 手动修改配置文件时注意保持路径相对性正确