# recommend report-all

## 概述

生成综合分析报告的配置文件，包括中尺度重构数据和代表年数据的时间序列分析配置。该命令会在 `report-masts/` 目录下生成多个 TOML 配置文件，用于执行全面的数据质量评估和统计分析。

## 语法

```bash
julia bin/CleanMast.jl recommend report-all <项目目录>
```

## 实现位置

**核心实现**: `src/ReportAllMasts/RecommendReportAllCommand.jl` (待实现)

## 功能流程

1. **数据源扫描**
   - 扫描 `reconstruct-meso/` 目录下的重构数据
   - 扫描 `representative-year/` 目录下的校准数据
   - 扫描 `reconstruct-single/`, `clean/` 等各处理阶段数据
   - 验证数据文件完整性和格式

2. **统一配置生成**
   - 将所有分析配置文件集中到 `report-masts/` 目录
   - 为中尺度重构数据生成时间序列分析配置
   - 为代表年数据生成时间序列分析配置
   - 为各处理阶段生成对比分析配置
   - 配置综合报告生成参数

3. **标准化目录结构**
   - 替代项目根目录下散乱的分析配置文件
   - 在 `report-masts/` 下创建统一的配置管理
   - 生成标准化的分析配置模板
   - 设置报告输出路径和格式

## 生成的配置文件

### 完整的 report-masts/ 目录结构
```
report-masts/
├── report-timeseries-meso.toml       # 中尺度重构数据时间序列分析
├── report-timeseries-rep.toml        # 代表年数据时间序列分析
├── report-recovery.toml              # 数据恢复率分析
├── report-cross-mast.toml            # 跨塔关联分析
└── report-reconstruct-single.yaml    # 单塔重构质量分析
```

**注意**: 这两个时间序列配置文件都使用同一个 `report timeseries` 命令，只是分析不同的数据源。

### 1. 中尺度重构分析配置

#### `report-masts/report-timeseries-meso.toml`
```toml
# 中尺度重构数据时间序列分析配置
# 路径相对于 report-masts/ 目录

[[masts]]
name = "M230016"
    [masts.input]
    data = "../reconstruct-meso/M230016.csv"
    sensors = "../reconstruct-meso/M230016.sensors.yaml"

[[masts]]
name = "M230015"
    [masts.input]
    data = "../reconstruct-meso/M230015.csv"
    sensors = "../reconstruct-meso/M230015.sensors.yaml"

[output]
path = "timeseries-meso"
```

### 2. 代表年分析配置

#### `report-masts/report-timeseries-rep.toml`
```toml
# 代表年数据时间序列分析配置
# 路径相对于 report-masts/ 目录

[[masts]]
name = "M230016"
    [masts.input]
    data = "../representative-year/M230016.csv"
    sensors = "../representative-year/M230016.sensors.yaml"

[[masts]]
name = "M230015"
    [masts.input]
    data = "../representative-year/M230015.csv"
    sensors = "../representative-year/M230015.sensors.yaml"

[output]
path = "timeseries-rep"
```

### 3. 数据恢复分析配置

#### `report-masts/report-recovery.toml`
```toml
# 数据恢复率分析配置
# 路径相对于 report-masts/ 目录

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

## 相关文件

- **配置文件**: 生成多个分析配置文件
- **处理命令**: [report all](../report-all.md)
- **配置类型**: `src/Types/ReportAllConfig.jl` (待创建)

## 生成的配置用途

生成的配置文件用于：

1. **中尺度重构分析**: `julia bin/CleanMast.jl report timeseries ./report-masts/report-timeseries-meso.toml`
2. **代表年分析**: `julia bin/CleanMast.jl report timeseries ./report-masts/report-timeseries-rep.toml`
3. **清理数据分析**: `julia bin/CleanMast.jl report clean ./projects/my-project`
4. **代表年校正分析**: `julia bin/CleanMast.jl report representative-year ./projects/my-project`
5. **数据恢复分析**: `julia bin/CleanMast.jl analyze recovery ./report-masts/analyze-recovery.toml`
6. **综合报告生成**: `julia bin/CleanMast.jl report all ./project` (自动使用所有配置)

## 下一步操作

配置生成后，可以执行以下步骤：

1. **检查配置**: 验证生成的 TOML 文件参数正确性
2. **执行综合分析**: `julia bin/CleanMast.jl report all ./project`
3. **审核报告**: 检查生成的分析报告和可视化结果
4. **导出成果**: 整理最终的技术报告和数据分析结果

