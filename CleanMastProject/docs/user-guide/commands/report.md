# report 命令参考

`report` 命令用于生成各种数据分析报告，包括数据清理、恢复状态、跨塔相关性、代表年校准等。

## 命令列表

| 命令 | 功能描述 |
|------|----------|
| [clean](#clean) | 生成数据清理报告 |
| [all](#all) | 生成所有综合报告 |
| [recovery](#recovery) | 生成数据恢复状态报告 |
| [frozen-period](#frozen-period) | 生成冻结传感器期检测报告 |
| [representative-year](#representative-year) | 生成代表年校准分析报告 |
| [cross-mast](#cross-mast) | 生成跨塔相关性分析报告 |
| [timeseries](#timeseries) | 生成时序分析报告 |
| [reconstruct-single](#reconstruct-single) | 生成单塔重构效果报告 |
| [reconstruct-meso](#reconstruct-meso) | 生成中尺度重构质量报告 |
| [meso-timeseries](#meso-timeseries) | 生成中尺度年气候报告 |

---

## clean

生成数据清理报告，对比原始数据与清洗后数据。

**用法：**
```bash
# 第一步：生成配置
julia bin/CleanMast.jl recommend report-clean ./projects/my-project

# 第二步：生成报告
julia bin/CleanMast.jl report clean ./projects/my-project/report-masts/report-clean.toml
```

**功能：**
1. 加载 `report-clean.toml` 配置文件
2. 加载原始数据和清洁数据文件
3. 加载 `process-stats/` 中的违规摘要
4. 生成中文 Typst 报告，包含：
   - 执行摘要
   - 传感器清单
   - 数据覆盖率对比
   - 规则违规分析

**输出文件：**
- `report-masts/clean/report.typ`：主中文报告
- `report-masts/clean/generation.log`：生成日志
- `report-masts/clean/generation.err`：错误日志
- `report-masts/clean/plots/`：生成的图表

---

## all

一次性生成所有综合塔分析报告。

**用法：**
```bash
julia bin/CleanMast.jl report all ./projects/my-project
```

**功能：**
生成四个综合报告：

1. **Clean Report** - 原始数据与清洁数据对比及违规分析
2. **Recovery Report** - 跨重构阶段的数据覆盖率
3. **Cross-Mast Report** - 塔对之间的相关性分析
4. **Representative Year Report** - 校准分析及效果

**前置条件：**
- `process-clean.toml`（用于清理报告）
- `reconstruct-meso.toml`（用于恢复报告）
- `analyze-reconstruct-cross.toml`（用于跨塔报告）
- `representative-year.toml`（用于代表年报告）

**输出文件：**
- `report-masts/clean/report.typ`：清洁数据分析
- `report-masts/recovery/recovery-report.typ`：重构效果
- `report-masts/cross-mast/report.typ`：跨塔相关性分析
- `report-masts/representative-year/report.typ`：校准分析

**注意：** 如果某些配置缺失，命令将继续生成可用报告。

---

## recovery

生成数据恢复状态报告，展示重构效果。

**用法：**
```bash
julia bin/CleanMast.jl report recovery ./projects/my-project/report-masts/report-recovery.toml
```

**功能：**
1. 加载 `report-recovery.toml` 配置
2. 分析各重构阶段数据：
   - 塔影处理（初始处理数据）
   - 单塔重构
   - 跨塔重构
   - 中尺度重构
3. 计算每个传感器的恢复统计
4. 生成中文 Typst 报告：
   - 每个塔的恢复统计表
   - 显示重构效果的柱状图
   - 总体恢复统计

**输出文件：**
- `report-masts/recovery/recovery-report.typ`：主中文报告

**包含表格：**
- 初始缺失
- 同塔插补
- 异塔插补
- 中尺度插补
- 最终缺失

---

## frozen-period

生成传感器冻结期检测报告。

**用法：**
```bash
julia bin/CleanMast.jl report frozen-period ./projects/my-project/report-masts/report-frozen-period.toml
```

**功能：**
1. 加载 `report-frozen-period.toml` 配置
2. 对每个塔，加载原始数据并使用所有阈值集检测冻结期
3. 基于多条件标准检测冻结期（温度、风稳定性、持续时间）
4. 生成中文 Typst 报告：
   - 每个阈值集的月度冻结持续时间表（加热型、非加热型）
   - 月度缺失数据持续时间表
   - RH 传感器可用性状态
   - 检测方法文档

**输出文件：**
- `report-masts/frozen-period/frozen-period-report.typ`：主中文报告

**包含分析：**
- 每月冻结天数和缺失天数
- 加热型和非加热型传感器阈值的单独分析

---

## representative-year

生成代表年校准分析报告。

**用法：**
```bash
julia bin/CleanMast.jl report representative-year ./projects/my-project
```

**功能：**
1. 加载 `representative-year.toml` 配置
2. 分析每个塔-中尺度对的校准结果：
   - 气候学与训练期比较
   - 代表年选择及效果
   - 16方向详细分析（斜率和截距）
3. 过滤分析传感器到 ≥100m 高度或最高可用传感器
4. 生成中英文 Typst 报告：
   - 执行摘要
   - 气候学分析
   - 16方向扇区分析
   - 传感器校正分析
   - 性能指标和建议

**输出文件：**
- `representative-year-report/report.typ`：主双语报告
- `representative-year-report/tables/`：单独分析表格
- `representative-year-report/data/`：CSV 数据导出

**前置条件：**
- `representative-year.toml` 配置文件
- `process-stats/` 中的校准结果（如果应用了校准）
- 中尺度数据源用于气候学分析

---

## cross-mast

生成跨塔相关性分析报告。

**用法：**
```bash
julia bin/CleanMast.jl report cross-mast path/to/report-cross-mast.toml
```

**输入配置：**
TOML 配置文件应指定：
- 多个塔及其重构时序数据文件和传感器配置
- 分析设置包括输出目录和报告格式
- 语言偏好（默认：中文）

**功能：**
对每个塔对，生成：
- 风速相关性分析（散点图和回归参数）
- 风向关系分析（偏移量和标准差）
- 数据覆盖率统计和重叠持续时间
- 每个塔对的单独 PNG 图表
- 每个塔对的单独 CSV 数据导出
- 带嵌入式可视化的综合中文 Typst 报告

**输出文件：**
- `report.typ`：主中文报告（包含所有分析结果）
- `plots/`：单独图表文件（`{目标}_{源}_speed_correlations.png` 等）
- `tables/`：每个塔对的单独表格文件
- `data/`：CSV 导出用于进一步分析

---

## timeseries

生成时序分析报告。

**用法：**
```bash
julia bin/CleanMast.jl report timeseries path/to/analyze.yaml
julia bin/CleanMast.jl report timeseries path/to/analyze.toml
julia bin/CleanMast.jl report timeseries path/to/analyze.json
```

**输入配置：**
配置文件应指定：
- 多个塔及其数据文件和传感器配置
- 每个塔的空气密度设置
- 结果输出目录
- 可选的 DOCX 报告设置

**功能：**
对每个塔，生成：
- 风时间分析（时序、日/月模式）
- 垂直剖面分析
- 风向频率和功率分布
- 风玫瑰图（频率和功率）
- 湍流强度分析（包含 `meteodyn_ti.txt`）
- 韦布尔分布分析

---

## reconstruct-single

生成单塔重构前后对比报告。

**用法：**
```bash
julia bin/CleanMast.jl report reconstruct-single path/to/analyze-reconstruct-single.yaml
```

**输入配置：**
YAML 配置文件应指定：
- 多个塔及其重构前后数据文件和传感器配置
- 结果输出目录（默认：`./analyze-reconstruct-single`）

**功能：**
对每个塔，生成：
- 重构前后缺失数据点数
- 重构率和数据覆盖率
- 高度间风速相关性的 R² 矩阵
- 高度间风向差异的平均值和标准差
- 综合中文 Typst 报告

---

## reconstruct-meso

生成中尺度重构质量分析报告。

**用法：**
```bash
julia bin/CleanMast.jl report reconstruct-meso path/to/report-masts/report-reconstruct-meso.toml
```

**输入配置：**
TOML 配置文件应指定：
- 多个塔及其输入数据文件和中尺度源名称
- 多个中尺度数据源
- 分析设置包括输出目录和图表偏好

**功能：**
对每个塔-中尺度对，生成：
- RMSE（均方根误差）指标
- Pearson 相关系数
- 顶部3个风速传感器（statType = avg）的散点图及拟合回归线
- CSV 数据导出用于进一步分析
- 带嵌入式可视化的综合中文 Typst 报告

**输出文件：**
- `report.typ`：主中文报告（包含所有分析结果）
- `plots/`：单独图表文件（`{塔}_{中尺度}_sensors.png`）
- `data/`：CSV 导出（`{塔}_{中尺度}_metrics.csv`）

---

## meso-timeseries

生成中尺度时序年气候分析报告。

**用法：**
```bash
julia bin/CleanMast.jl report meso-timeseries path/to/report-masts/report-meso-timeseries.toml
```

**输入配置：**
TOML 配置文件应指定：
- 多个中尺度数据集及其数据文件和传感器配置
- 结果输出目录

**功能：**
对每个中尺度数据集，生成：
- 使用最高传感器的年风速气候学分析
- 年均值、气候学和差异的 CSV 表格
- 显示年时序和气候学线的 SVG 图表
- 带摘要统计的 Typst 报告

**输出文件：**
- `annual_climatology.typ`：主中文报告（包含分析结果）
- `annual_climatology.csv`：统计年数据表格
- `annual_climatology.svg`：可视化图表

---

## 使用建议

1. **推荐工作流程**：
   - 先运行 `recommend report-*` 生成配置
   - 再运行 `report *` 生成实际报告

2. **批量报告**：使用 `report all` 一次性生成所有报告

3. **语言支持**：大多数报告默认生成中文版本

4. **输出目录**：报告通常输出到 `report-masts/` 子目录
