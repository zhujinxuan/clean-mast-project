# report all

## 概述

`report all` 命令执行完整的分析和报告生成流程，自动运行所有必要的分析步骤，生成综合的技术报告。

## 实现位置

**核心实现**: `src/ReportAllMasts/ReportAllMastsCommand.jl`

## 自动执行分析

`report all` 命令按以下顺序自动执行完整的分析流程：

### 1. [中尺度重构数据分析](report/analyze-reconstruct-meso.md)
- 分析中尺度重构后的数据质量
- 生成风资源评估报告
- 评估重构效果和不确定度

### 2. [代表年数据分析](report/analyze-representative-year.md)
- 分析代表年校准后的数据
- 生成标准化风资源报告
- 评估校准效果

## 语法

```bash
julia bin/CleanMast.jl report all <项目目录>
```

## 前置条件

- 必须先完成 `process all` 或相应的处理步骤
- 必须先完成 `recommend report-all` 生成配置文件
- 存在 `report-masts/` 目录及其配置文件

## 执行特点

### 自动配置使用
`report all` 会自动使用 `report-masts/` 目录中的所有配置文件：
- 检查并加载所有分析配置
- 按优先级执行分析任务
- 生成统一的综合报告

### 智能分析调度
- **并行执行**: 独立分析任务并行运行
- **依赖管理**: 自动处理分析间的依赖关系
- **资源优化**: 智能分配计算资源

### 统一报告生成
- **综合报告**: 整合所有分析结果
- **多格式输出**: PDF、HTML、数据表格
- **中英文支持**: 根据配置选择报告语言

## 分析内容

### 1. 风资源评估
- 风速分布分析和威布尔拟合
- 风向玫瑰图和风向频率分析
- 湍流强度分析
- 垂直风切变分析
- 极值风速分析

### 2. 数据质量评估
- 各处理阶段数据完整性分析
- 重构质量和不确定度评估
- 数据一致性检查
- 异常值识别和统计

### 3. 工程参数计算
- IEC 标准风机级别评估
- EN 标准工程参数
- 结构设计参数
- 安全系数计算

## 输出结构

```
report-masts/
├── reconstruct-meso/           # 中尺度重构分析结果
│   ├── report.pdf
│   ├── report.html
│   └── data/
├── representative-year/        # 代表年分析结果
│   ├── report.pdf
│   ├── report.html
│   └── data/
├── recovery/                   # 数据恢复分析结果
│   └── recovery-report.pdf
└── comprehensive-report.pdf    # 综合技术报告
```

## 相关命令

如需单独执行特定分析，可使用以下独立命令：

- [analyze timeseries](report/analyze-timeseries.md) - 时间序列分析
- [analyze reconstruct-single](report/analyze-reconstruct-single.md) - 单塔重构质量分析
- [analyze reconstruct-cross](report/analyze-reconstruct-cross.md) - 跨塔重构分析
- [analyze recovery](report/analyze-recovery.md) - 数据恢复分析

## 配置生成

`report all` 会自动使用 `recommend report-all` 生成的配置：

```bash
# 生成所有分析配置文件
julia bin/CleanMast.jl recommend report-all ./project

# 执行综合分析报告
julia bin/CleanMast.jl report all ./project
```

## 示例用法

```bash
# 完整的分析流程
julia bin/CleanMast.jl recommend report-all projects/windfarm-170
julia bin/CleanMast.jl report all projects/windfarm-170

# 输出示例
Generating comprehensive analysis reports...
Step 1/4: Analyzing reconstruct-meso data...    ✓ Complete
Step 2/4: Analyzing representative-year data... ✓ Complete
Step 3/4: Analyzing recovery statistics...      ✓ Complete
Step 4/4: Generating comprehensive report...    ✓ Complete

All analysis reports generated successfully!
Reports available in: projects/windfarm-170/report-masts/
```

## 报告特点

### 多语言支持
- 报告主要使用中文生成
- 技术术语保持国际标准
- 图表标签和说明中文化

### 可视化质量
- 高质量的统计图表
- 交互式网页报告
- 专业的PDF输出
- 科学级的数据可视化

### 数据质量评估
- 自动数据质量检查
- 异常值识别和报告
- 完整性评估
- 可靠性指标

## 注意事项

- 确保先完成数据处理流程 (`process all`)
- 必须先生成分析配置 (`recommend report-all`)
- 检查 `report-masts/` 目录中的配置文件
- 报告生成可能需要较长时间
- 确保有足够的磁盘空间存储报告文件
- 某些分析需要特定的软件依赖（如Typst）