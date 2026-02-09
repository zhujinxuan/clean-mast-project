# recommend 命令参考

`recommend` 命令用于为 CleanMast 各处理阶段自动生成配置文件。这些命令分析项目结构并生成适合特定数据配置的 TOML 配置文件。

## 命令列表

| 命令 | 功能描述 |
|------|----------|
| [parse-sensors](#parse-sensors) | 生成传感器解析配置 |
| [process-clean](#process-clean) | 生成数据清理配置 |
| [tower-shading](#tower-shading) | 生成塔影检测配置 |
| [reconstruct-single](#reconstruct-single) | 生成单塔重构配置 |
| [train-meso](#train-meso) | 生成中尺度训练配置 |
| [reconstruct-meso](#reconstruct-meso) | 生成中尺度重构配置 |
| [train-reconstruct-cross](#train-reconstruct-cross) | 生成跨塔训练配置 |
| [analyze-reconstruct-cross](#analyze-reconstruct-cross) | 生成跨塔分析配置 |
| [reconstruct-cross](#reconstruct-cross) | 生成跨塔重构配置 |
| [representative-year](#representative-year) | 生成代表年配置 |
| [wt-timeseries](#wt-timeseries) | 生成风机时间序列配置 |
| [report-clean](#report-clean) | 生成清理报告配置 |
| [report-recovery](#report-recovery) | 生成恢复报告配置 |
| [report-frozen-period](#report-frozen-period) | 生成冻结期报告配置 |
| [report-cross-mast](#report-cross-mast) | 生成跨塔报告配置 |
| [report-reconstruct-single](#report-reconstruct-single) | 生成单塔重构报告配置 |
| [report-reconstruct-meso](#report-reconstruct-meso) | 生成中尺度重构报告配置 |
| [report-all](#report-all) | 生成所有报告配置 |
| [report-timeseries-meso](#report-timeseries-meso) | 生成中尺度时序报告配置 |
| [report-timeseries-rep](#report-timeseries-rep) | 生成代表年时序报告配置 |
| [report-meso-timeseries](#report-meso-timeseries) | 生成中尺度年气候报告配置 |

## parse-sensors

生成 `parse-sensors.toml` 配置文件，扫描项目目录识别数据文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend parse-sensors ./projects/my-project
```

**功能：**
- 扫描项目目录查找 `masts/*.{csv,txt}` 文件（假设为 NRG 格式）
- 扫描项目目录查找 `mesos/*.{csv,txt}` 文件（假设为 freemeso-meso 格式）
- 自动生成包含默认传感器格式配置的 `parse-sensors.toml`

**输出文件：**
- `parse-sensors.toml`：传感器数据解析配置

---

## process-clean

生成 `process-clean.toml` 数据清理配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend process-clean ./projects/my-project
```

**前置条件：**
- 项目目录包含 `parse-sensors.toml`

**输出文件：**
- `process-clean.toml`：数据清理规则和参数配置

---

## tower-shading

生成 `tower-shading.toml` 塔影检测和校正配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend tower-shading ./projects/my-project
```

**前置条件：**
- 项目目录包含 `config.yaml`

**输出文件：**
- `tower-shading.toml`：塔影检测配置

---

## reconstruct-single

生成 `reconstruct-single.toml` 单塔数据重构配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend reconstruct-single ./projects/my-project
```

**前置条件：**
- 项目目录包含 `tower-shading.toml`

**输出文件：**
- `reconstruct-single.toml`：单塔重构配置

---

## train-meso

生成 `train-meso.toml` 中尺度模型训练配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend train-meso ./projects/my-project
```

**前置条件：**
- 项目目录包含 `reconstruct-single.toml`

**输出文件：**
- `train-meso.toml`：中尺度模型训练配置

---

## reconstruct-meso

生成 `reconstruct-meso.toml` 中尺度数据重构配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend reconstruct-meso ./projects/my-project
julia bin/CleanMast.jl recommend reconstruct-meso ./projects/my-project --cluster-threshold 0.7 --threshold-period 90
```

**参数：**
- `dir`：项目目录路径
- `--cluster-threshold`：重叠阈值，用于塔群聚类（默认：0.8）
- `--threshold-period`：聚类的最小交叉期天数（默认：120天）

**前置条件：**
- 项目目录包含 `train-meso.toml`

**功能：**
- 当多个塔有重叠数据时，对它们进行聚类
- 同一聚类共享相同的重构期

**输出文件：**
- `reconstruct-meso.toml`：中尺度重构配置

---

## train-reconstruct-cross

生成 `train-reconstruct-cross.toml` 跨塔训练配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend train-reconstruct-cross ./projects/my-project
```

**前置条件：**
- 项目目录包含重构后的塔数据

**输出文件：**
- `train-reconstruct-cross.toml`：跨塔训练配置

---

## analyze-reconstruct-cross

生成 `analyze-reconstruct-cross.toml` 跨塔分析配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend analyze-reconstruct-cross ./projects/my-project
```

**功能：**
- 检测可用的塔数据文件
- 分析传感器配置
- 设置输出目录
- 生成跨塔相关性研究的默认分析参数

**输出文件：**
- `analyze-reconstruct-cross.toml`：跨塔分析配置

**使用方式：**
```bash
julia bin/CleanMast.jl report cross-mast path/to/analyze-reconstruct-cross.toml
```

---

## reconstruct-cross

生成 `reconstruct-cross.toml` 跨塔重构配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend reconstruct-cross ./train-reconstruct-cross
julia bin/CleanMast.jl recommend reconstruct-cross ./train-reconstruct-cross ./output --min-coverage 25.0
```

**参数：**
- `train_results_path`：训练结果路径
- `output_dir`：配置文件输出目录（默认：`"./"`）
- `--min-coverage`：合格的最少数据覆盖天数（默认：30.0）

**输出文件：**
- `reconstruct-cross.toml`：跨塔重构配置

---

## representative-year

生成 `representative-year.toml` 代表年校准配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend representative-year ./projects/my-project
```

**前置条件：**
- 项目目录包含 `reconstruct-meso.toml`

**输出文件：**
- `representative-year.toml`：代表年校准配置

---

## wt-timeseries

生成 `wt-timeseries.toml` 风机时间序列配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend wt-timeseries ./projects/my-project
```

**前置条件：**
- 项目目录包含 `representative-year.toml`

**输出文件：**
- `wt-timeseries.toml`：风机时间序列处理配置

---

## report-clean

生成 `report-clean.toml` 数据清理报告配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend report-clean ./projects/my-project
```

**前置条件：**
- 项目目录包含 `process-clean.toml`

**输出位置：**
- `report-masts/report-clean.toml`

**功能：**
- 配置原始数据和清洁数据源
- 预加载清理规则用于分析
- 生成层差参数用于表格生成

**使用方式：**
```bash
julia bin/CleanMast.jl report clean ./projects/my-project
```

---

## report-recovery

生成 `report-recovery.toml` 数据恢复状态报告配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend report-recovery ./projects/my-project
```

**前置条件：**
- 项目目录包含 `reconstruct-meso.toml`

**输出位置：**
- `report-masts/report-recovery.toml`

**功能：**
- 分析各重构阶段的数据恢复效果

---

## report-frozen-period

生成 `report-frozen-period.toml` 传感器冻结期检测报告配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend report-frozen-period ./projects/my-project
```

**前置条件：**
- 项目目录包含 `parse-sensors.toml`

**输出位置：**
- `report-masts/report-frozen-period.toml`

**功能：**
- 配置多阈值集（加热型和非加热型）用于不同传感器类型
- 检测传感器冻结期

**使用方式：**
```bash
julia bin/CleanMast.jl report frozen-period ./projects/my-project/report-masts/report-frozen-period.toml
```

---

## report-cross-mast

生成 `report-cross-mast.toml` 跨塔相关性报告配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend report-cross-mast ./projects/my-project
```

**前置条件：**
- 项目目录包含 `reconstruct-single.toml`

**输出位置：**
- `report-masts/report-cross-mast.toml`

---

## report-reconstruct-single

生成 `report-reconstruct-single.yaml` 单塔重构效果分析配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend report-reconstruct-single ./projects/my-project
```

**前置条件：**
- 项目目录包含重构配置

**功能：**
- 检测塔影处理前数据（重构前）
- 检测单塔重构输出数据（重构后）
- 配置重构效果比较参数
- 在 `report-masts/` 下设置输出目录

**使用方式：**
```bash
julia bin/CleanMast.jl report reconstruct-single path/to/report-masts/report-reconstruct-single.yaml
```

---

## report-reconstruct-meso

生成 `report-reconstruct-meso.toml` 中尺度重构质量分析报告配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend report-reconstruct-meso ./projects/my-project
```

**前置条件：**
- 项目目录包含 `reconstruct-meso.toml`

**输出位置：**
- `report-masts/report-reconstruct-meso.toml`

**功能：**
- 生成塔-中尺度对的质量分析报告
- 显示 RMSE 和相关性指标
- 顶部3个风速传感器的散点图

**使用方式：**
```bash
julia bin/CleanMast.jl report reconstruct-meso path/to/report-masts/report-reconstruct-meso.toml
```

---

## report-all

一次性生成所有报告 TOML 配置文件。

**用法：**
```bash
julia bin/CleanMast.jl recommend report-all ./projects/my-project
```

**功能：**
生成以下四个主要报告的配置文件：

1. **report-recovery.toml** - 跨重构阶段的数据恢复状态
2. **report-cross-mast.toml** - 跨塔相关性分析配置
3. **report-reconstruct-single.yaml** - 单塔重构效果分析

**输出位置：**
- `report-masts/` 目录

**前置条件：**
- `reconstruct-meso.toml`（用于恢复报告配置）
- `reconstruct-single.toml`（用于跨塔报告配置）
- `tower-shading.toml`（用于重构单塔报告配置）
- `process-clean.toml`（直接由清理报告使用）
- `representative-year.toml`（直接由代表年报告使用）

**使用方式：**
```bash
julia bin/CleanMast.jl report all ./projects/my-project
```

---

## report-timeseries-meso

生成 `report-timeseries-meso.toml` 中尺度重构数据时序分析报告配置。

**用法：**
```bash
julia bin/CleanMast.jl recommend report-timeseries-meso ./projects/my-project
```

**前置条件：**
- 项目目录包含 `reconstruct-meso.toml`

**输出位置：**
- `report-masts/report-timeseries-meso.toml`

**使用方式：**
```bash
julia bin/CleanMast.jl report timeseries ./projects/my-project/report-masts/report-timeseries-meso.toml
```

---

## report-timeseries-rep

生成 `report-timeseries-rep.toml` 代表年数据时序分析报告配置。

**用法：**
```bash
julia bin/CleanMast.jl recommend report-timeseries-rep ./projects/my-project
```

**前置条件：**
- 项目目录包含 `representative-year.toml`

**输出位置：**
- `report-masts/report-timeseries-rep.toml`

**使用方式：**
```bash
julia bin/CleanMast.jl report timeseries ./projects/my-project/report-masts/report-timeseries-rep.toml
```

---

## report-meso-timeseries

生成 `report-meso-timeseries.toml` 中尺度数据年气候分析报告配置。

**用法：**
```bash
julia bin/CleanMast.jl recommend report-meso-timeseries ./projects/my-project
```

**前置条件：**
- 项目目录包含 `parse-sensors.toml`

**输出位置：**
- `report-masts/report-meso-timeseries.toml`

**功能：**
- 使用每个中尺度数据集的最高风速传感器
- 计算每年的平均风速
- 计算气候学（多年平均）
- 生成显示年际变化的表格和图表

**使用方式：**
```bash
julia bin/CleanMast.jl report meso-timeseries ./projects/my-project/report-masts/report-meso-timeseries.toml
```

---

## 使用建议

1. **工作流程**：按顺序执行 recommend 命令，遵循数据处理流程
2. **先决条件**：确保前置配置文件存在
3. **配置文件修改**：生成后可手动编辑调整参数
4. **批量生成**：使用 `report-all` 一次性生成所有报告配置
