# 配置文件参考

## 概述

本文档提供所有 CleanMast 配置文件的完整参考，包括文件格式、字段定义和实现代码位置。

## 配置文件类型

### 处理配置文件

#### process-clean.toml
**用途**: 数据清理配置
**生成命令**: `julia bin/CleanMast.jl recommend process-clean <项目目录>`
**类型定义**: `src/Types/ProcessCleanConfig.jl`
**文档**: [recommend process-clean](../commands/recommend/process-clean.md)

#### tower-shading.toml
**用途**: 塔影校正配置
**生成命令**: `julia bin/CleanMast.jl recommend tower-shading <项目目录>`
**类型定义**: `src/Types/TowerShadingConfig.jl`
**文档**: [recommend tower-shading](../commands/recommend/tower-shading.md)

#### reconstruct-single.toml
**用途**: 单测风塔重构配置
**生成命令**: `julia bin/CleanMast.jl recommend reconstruct-single <项目目录>`
**类型定义**: `src/Types/ReconstructSingleConfig.jl`
**文档**: [recommend reconstruct-single](../commands/recommend/reconstruct-single.md)

#### train-meso.toml
**用途**: 中尺度模型训练配置
**生成命令**: `julia bin/CleanMast.jl recommend train-meso <项目目录>`
**类型定义**: `src/Types/TrainMesoConfig.jl`
**文档**: [recommend train-meso](../commands/recommend/train-meso.md)

#### reconstruct-meso.toml
**用途**: 中尺度重构配置
**生成命令**: `julia bin/CleanMast.jl recommend reconstruct-meso <项目目录>`
**类型定义**: `src/Types/ReconstructMesoConfig.jl`
**文档**: [recommend reconstruct-meso](../commands/recommend/reconstruct-meso.md)

#### train-reconstruct-cross.toml
**用途**: 跨测风塔模型训练配置
**生成命令**: `julia bin/CleanMast.jl recommend train-reconstruct-cross <项目目录>`
**类型定义**: `src/Types/TrainReconstructCrossConfig.jl`
**文档**: [recommend train-reconstruct-cross](../commands/recommend/train-reconstruct-cross.md)

#### reconstruct-cross.toml
**用途**: 跨测风塔重构配置
**生成命令**: `julia bin/CleanMast.jl recommend reconstruct-cross <项目目录>`
**类型定义**: `src/Types/ReconstructCrossConfig.jl`
**文档**: [recommend reconstruct-cross](../commands/recommend/reconstruct-cross.md)

### 项目配置文件

#### parse-sensors.toml
**用途**: 传感器解析配置
**生成命令**: `julia bin/CleanMast.jl recommend parse-sensors <项目目录>`
**类型定义**: `src/Types/ParseSensorsConfig.jl`

### 分析配置文件

#### report-masts/ 配置目录
**用途**: 统一的分析配置管理
**生成命令**: `julia bin/CleanMast.jl recommend report-all <项目目录>`
**配置类型**: 多种分析配置类型
**文档**: [recommend report-all](../commands/recommend/report-all.md)

包含的配置文件：
- `analyze-reconstruct-meso.toml` - 中尺度重构数据分析
- `analyze-representative-year.toml` - 代表年数据分析
- `analyze-clean.toml` - 清理数据质量分析
- `analyze-reconstruct-single.toml` - 单塔重构质量分析
- `analyze-recovery.toml` - 数据恢复率分析
- `analyze-comparison.toml` - 各阶段对比分析

#### analyze-rep.toml (传统配置)
**用途**: 代表年分析配置
**类型定义**: `src/Types/AnalyzeTimeSeriesConfig.jl`
**注意**: 建议迁移到 `report-masts/` 目录结构

## 配置文件结构示例

### 基本结构模式

#### TimeSeriesSource 结构
**定义位置**: `src/Types/Utils.jl`
```toml
[input]  # 或 [output]
data = "./path/to/data.csv"
sensors = "./path/to/sensors.yaml"  # 或 .toml
```

#### 测风塔配置 (Mast)
```toml
[[masts]]
name = "测风塔名称"
    [masts.input]
    data = "./输入数据路径.csv"
    sensors = "./输入传感器配置.yaml"
    [masts.output]
    data = "./输出数据路径.csv"
    sensors = "./输出传感器配置.yaml"
```

#### 中尺度数据配置 (Meso)
```toml
[[mesos]]
name = "era5-002824"
    [mesos.input]
    data = "./raw/era5-002824.csv"
    sensors = "./raw/era5-002824.sensors.toml"
```

### 具体配置示例

#### process-clean.toml
```toml
[[masts]]
name = "pn-002824"
rules = "formats/clean/default.toml"
    [masts.input]
    data = "./raw/pn-002824.csv"
    sensors = "./raw/pn-002824.sensors.toml"
    [masts.output]
    data = "./clean/pn-002824.csv"
    sensors = "./clean/pn-002824.sensors.yaml"
```

#### train-meso.toml
```toml
# 中尺度数据源
[[mesos]]
name = "era5-002824"
    [mesos.input]
    data = "./raw/era5-002824.csv"
    sensors = "./raw/era5-002824.sensors.toml"

# 测风塔数据源
[[masts]]
name = "pn-002824"
    [masts.input]
    data = "./tower-shading/pn-002824.csv"
    sensors = "./tower-shading/pn-002824.sensors.yaml"

# 模型配置
[[models]]
mast_name = "pn-002824"
meso_name = "era5-002824"
method = "16-sector"
output = "./meso-models/pn-002824/era5-002824/windspeed/16-sector.jld2"
```

#### reconstruct-meso.toml
```toml
[[mesos]]
name = "era5-002824"
    [mesos.input]
    data = "./raw/era5-002824.csv"
    sensors = "./raw/era5-002824.sensors.toml"

[[masts]]
name = "pn-002824"
    [masts.input]
    data = "./reconstruct-single/pn-002824.csv"
    sensors = "./reconstruct-single/pn-002824.sensors.yaml"
    [masts.output]
    data = "./reconstruct-meso/pn-002824.csv"
    sensors = "./reconstruct-meso/pn-002824.sensors.yaml"
    [masts.time_range]
    min = 2024-01-01T00:00:00.000Z
    max = 2025-01-31T23:59:59.000Z
    [masts.models.windspeed]
    method = "1-sector"
    model_file = "./meso-models/pn-002824/era5-002824/windspeed/1-sector.jld2"
    meso_name = "era5-002824"
    [masts.models.winddirection]
    method = "constant-offset"
    model_file = "./meso-models/pn-002824/era5-002824/winddirection/constant-offset.jld2"
    meso_name = "era5-002824"
```

#### train-reconstruct-cross.toml
```toml
# 测风塔数据源配置
[[masts]]
name = "pn-002824"
    [masts.input]
    data = "./reconstruct-single/pn-002824.csv"
    sensors = "./reconstruct-single/pn-002824.sensors.yaml"

[[masts]]
name = "pn-013945"
    [masts.input]
    data = "./reconstruct-single/pn-013945.csv"
    sensors = "./reconstruct-single/pn-013945.sensors.yaml"

# 训练参数配置
[train]
min_overlap_days = 90.0
max_std_deviation = 45.0
min_data_points = 200
output_dir = "./train-reconstruct-cross"
max_abs_offset = 45.0
min_correlation = 0.7
exclude_nan_results = true
```

#### reconstruct-cross.toml
```toml
# 训练元数据信息
[training_metadata]
qualified_direction_pairs = 0
total_mast_pairs = 6
train_results_file = "projects/pn-3masts/train-reconstruct-cross/train-results.toml"
qualified_speed_pairs = 6
training_date = "2025-09-20T01:10:04.636"

# 测风塔重构配置
[[masts]]
name = "pn-002824"
    [masts.input]
    data = "./reconstruct-single/pn-002824.csv"
    sensors = "./reconstruct-single/pn-002824.sensors.yaml"
    [masts.output]
    data = "./reconstruct-cross/pn-002824_reconstructed.csv"
    sensors = "./reconstruct-cross/pn-002824_reconstructed.sensors.yaml"

# 重构设置
[settings]
min_confidence = 0.7
max_direction_uncertainty = 45.0
backup_originals = true
output_dir = "./reconstruct-cross"
preserve_existing = true
generate_reports = true

# 重构优先级配置
[[reconstruction_priorities]]
priority_level = 1
min_correlation = 0.7
max_direction_std = 15.0

    [[reconstruction_priorities.jobs]]
    model_dir = "train-reconstruct-cross/cross-mast-models/pn-013945/pn-002824"
    priority = 1
    variables = ["windspeed"]
    target_mast = "pn-013945"
    speed_correlation = 0.8895
    source_mast = "pn-002824"
    direction_std = 24.54
```

## 类型系统结构

### 核心类型定义

```julia
# src/Types/Utils.jl
struct TimeSeriesSource
    data::String      # 数据文件路径
    sensors::String   # 传感器配置文件路径
end

# 基础测风塔配置
struct Mast
    name::String
    input::TimeSeriesSource
    output::TimeSeriesSource
end
```

### 配置类型层次

- `ProcessCleanConfig.jl` - 数据清理配置
- `TowerShadingConfig.jl` - 塔影校正配置
- `ReconstructSingleConfig.jl` - 单塔重构配置
- `TrainMesoConfig.jl` - 中尺度训练配置
- `ReconstructMesoConfig.jl` - 中尺度重构配置
- `TrainReconstructCrossConfig.jl` - 跨塔训练配置
- `ReconstructCrossConfig.jl` - 跨塔重构配置
- `ParseSensorsConfig.jl` - 传感器解析配置
- `AnalyzeTimeSeriesConfig.jl` - 时间序列分析配置
- `ReportRecoveryConfig.jl` - 数据恢复分析配置

## 配置文件工作流

### 1. 自动生成
```bash
# 按处理顺序生成配置
julia bin/CleanMast.jl recommend parse-sensors ./project
julia bin/CleanMast.jl recommend process-clean ./project
julia bin/CleanMast.jl recommend tower-shading ./project
julia bin/CleanMast.jl recommend reconstruct-single ./project
julia bin/CleanMast.jl recommend train-reconstruct-cross ./project  # 可选：跨塔训练
julia bin/CleanMast.jl recommend reconstruct-cross ./project       # 可选：跨塔重构
julia bin/CleanMast.jl recommend train-meso ./project
julia bin/CleanMast.jl recommend reconstruct-meso ./project

# 生成分析配置（替代散乱的分析配置文件）
julia bin/CleanMast.jl recommend report-all ./project
```

### 2. 配置验证
- 类型验证：Julia 类型系统自动验证
- 路径检查：确保文件路径存在
- 依赖检查：验证前置步骤完成

### 3. 配置继承
后续步骤自动从前一步的输出生成输入路径：
- `clean/` → `tower-shading/` 输入
- `tower-shading/` → `reconstruct-single/` 输入
- `reconstruct-single/` → `train-reconstruct-cross/` 输入（可选）
- `reconstruct-single/` → `reconstruct-cross/` 输入（可选）
- `reconstruct-single/` → `train-meso/` 测风塔数据

## 最佳实践

### 配置管理
- 使用 `recommend` 命令自动生成配置
- 将配置文件纳入版本控制
- 为不同项目建立配置模板

### 路径约定
- 使用相对路径提高可移植性
- 保持一致的目录命名规范
- 避免路径中的特殊字符

### 参数调优
- 根据项目特点调整默认参数
- 记录参数修改的原因和效果
- 参考示例项目 `projects/pn-3masts/`

## 迁移说明

### 从散乱配置到统一管理
推荐使用 `recommend report-all` 生成的 `report-masts/` 目录结构，替代项目根目录下的散乱分析配置文件：

**传统方式** (不推荐):
```
project/
├── analyze-rep.toml
├── analyze-meso.toml
├── analyze-timeseries.yaml
└── ...
```

**推荐方式**:
```
project/
└── report-masts/
    ├── analyze-reconstruct-meso.toml
    ├── analyze-representative-year.toml
    ├── analyze-clean.toml
    ├── analyze-reconstruct-single.toml
    ├── analyze-recovery.toml
    └── analyze-comparison.toml
```

### 迁移步骤
1. 使用 `julia bin/CleanMast.jl recommend report-all ./project` 生成新配置
2. 验证生成的配置文件正确性
3. 使用 `julia bin/CleanMast.jl report all ./project` 执行分析
4. 逐步废弃根目录下的旧配置文件

## 相关文档

- [recommend 命令](../commands/recommend/) - 配置生成命令
- [process 命令](../commands/process/) - 数据处理命令
- [report 命令](../commands/report-all.md) - 分析报告命令
- [开发者指南](../../development/) - 类型系统设计