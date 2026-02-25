# Reporting 组件

## 概述

Reporting 是 CleanMast 的报告生成组件，负责将处理后的数据转换为标准化报告文档。该组件汇总所有处理阶段的数据分析结果，生成面向工程师和项目决策者的专业报告。

Reporting 作为数据处理流水线的最终环节，接收来自 ParseSensors、DataClean、ReconstructSingle、ReconstructMeso、RepresentativeYear 等上游组件的输出数据，将其整合为结构化的分析报告。

## 职责

Reporting 组件的核心职责包括：

- **数据聚合**：整合来自多个处理阶段的数据和统计结果
- **报告生成**：生成符合行业标准的专业分析报告
- **多格式输出**：支持 Typst PDF、DOCX、CSV 等多种输出格式
- **可视化呈现**：将分析结果以图表和表格形式展示

### 报告类型

Reporting 组件支持以下类型的报告生成：

| 报告类型 | 命令 | 说明 |
|---------|------|------|
| 数据清洗报告 | `report clean` | 分析原始数据与清洗后数据的差异，包含传感器清单、数据覆盖率、违规分析 |
| 恢复报告 | `report recovery` | 追踪数据在重建各阶段（塔影校正、单mast重建、跨mast重建、中尺度重建）的恢复效果 |
| 单mast重建报告 | `report reconstruct-single` | 分析单测风塔重建前后的数据相关性，包含风速相关性矩阵、风向差值分析 |
| 跨mast报告 | `report cross-mast` | 分析不同测风塔之间的相关性，评估跨mast重建的有效性 |
| 代表年报告 | `report representative-year` | 展示长期校准结果，比较气候学数据、训练数据与代表年数据的差异 |
| 时序报告 | `report timeseries` | 分析时间序列数据的统计特征，包含风玫瑰图、威布尔分布、湍流强度等 |
| 中尺度时序报告 | `report timeseries-meso` | 针对中尺度重建数据进行时间序列分析 |
| 中尺度重建报告 | `report reconstruct-meso` | 评估中尺度重建质量，比较中尺度数据与测风塔数据 |
| 冻结期报告 | `report frozen-period` | 检测传感器冻结期，分析温度、风速、风向的稳定性 |
| 综合报告 | `report all` | 生成上述所有报告的汇总 |

## 输入

Reporting 组件接收以下输入数据：

### 1. 处理后的时间序列数据

来自各处理阶段的输出数据，包括：

- **原始数据**（Raw Data）：ParseSensors 解析后的原始传感器数据
- **清洗数据**（Clean Data）：DataClean 处理后的数据，已应用范围验证、层差检查、结冰检测等规则
- **塔影校正数据**（Tower Shading Data）：经过塔影效应校正的数据
- **单mast重建数据**（Reconstructed Single Data）：基于mast内部相关性的重建数据
- **跨mast重建数据**（Reconstructed Cross Data）：基于多mast相关性的重建数据
- **中尺度重建数据**（Reconstructed Meso Data）：融合中尺度数据后的重建结果
- **代表年数据**（Representative Year Data）：经过长期校准的代表年数据

### 2. 统计数据

处理过程中生成的统计信息，包括：

- **违规统计**（Violation Statistics）：数据清洗过程中检测到的违规记录数量、类型和分布
- **覆盖率统计**（Coverage Statistics）：各传感器在不同时间段的数据完整率
- **相关性统计**（Correlation Statistics）：不同高度、不同mast之间的风速风向相关系数
- **重建统计**（Reconstruction Statistics）：重建数据量、重建比例、重建效果评估
- **冻结期统计**（Frozen Period Statistics）：各传感器的冻结期检测结果

### 3. 配置文件

报告生成的配置参数：

- **报告配置**（Report Configuration）：指定报告输出路径、报告格式、图表设置等
- **mast配置**（Mast Configuration）：各测风塔的传感器布局、数据文件路径
- **分析配置**（Analysis Configuration）：统计参数、阈值设置、输出选项

## 输出

Reporting 组件生成以下输出：

### 1. 文档输出

| 输出类型 | 格式 | 说明 |
|---------|------|------|
| 主报告 | Typst | 使用 Typst 排版系统生成的中文专业报告，包含图表、表格和分析结论 |
| 可选格式 | DOCX | 使用 Pandoc 将报告转换为 Word 格式，便于进一步编辑 |
| 可选格式 | PDF | 使用 Typst 编译器直接生成 PDF 文件 |

### 2. 数据输出

| 输出类型 | 格式 | 说明 |
|---------|------|------|
| 数据导出 | CSV | 统计结果、相关性矩阵等数据的表格化输出 |
| WT文件 | TXT | 符合 Meteodyn WT 软件格式的时间序列数据文件 |
| 图表文件 | PNG | 风玫瑰图、时序图、分布图等可视化结果 |

### 3. 输出目录结构

```
project/
├── report-masts/
│   ├── clean/
│   │   ├── report.typ      # 数据清洗报告
│   │   └── plots/          # 图表文件
│   ├── recovery/
│   │   ├── recovery-report.typ
│   │   └── plots/
│   ├── reconstruct-single/
│   │   ├── reconstruction_analysis_report.typ
│   │   └── plots/
│   ├── cross-mast/
│   │   ├── report.typ
│   │   ├── tables/
│   │   └── plots/
│   ├── representative-year/
│   │   ├── report.typ
│   │   ├── tables/
│   │   └── data/
│   ├── timeseries-meso/
│   │   └── [mast-name]/    # 每个mast的独立报告目录
│   ├── timeseries-rep/
│   │   └── [mast-name]/
│   ├── reconstruct-meso/
│   │   └── report.typ
│   └── frozen-period/
│       └── report.typ
```

## 依赖关系

### 上游依赖

Reporting 组件依赖以下组件提供输入数据：

```
Types (类型定义)
    ↓
ParseSensors → DataClean → TowerShading → ReconstructSingle
    ↓                           ↓                    ↓
    └───────────────────────────┴────────────────────┘
                              ↓
                       Reporting
                              ↓
              ReconstructMeso → RepresentativeYear
```

- **ParseSensors**：提供原始传感器数据和数据结构定义
- **DataClean**：提供清洗后的数据及违规统计信息
- **TowerShading**：提供塔影校正后的数据
- **ReconstructSingle**：提供单mast重建数据和相关性分析结果
- **ReconstructMeso**：提供中尺度重建数据和质量评估
- **ReconstructCross**：提供跨mast相关性分析结果
- **RepresentativeYear**：提供代表年校准数据和分析结果

### 外部依赖

- **Typst**：报告排版引擎，用于生成 PDF 格式报告
- **Pandoc**：文档转换工具，用于生成 DOCX 格式报告
- **Types 模块**：提供配置和数据结构类型定义
- **CleanMastUtils**：提供通用的工具函数

### 依赖关系图

```
┌─────────────────────────────────────────────────────────────┐
│                    上游处理组件                               │
├─────────────┬─────────────┬─────────────┬───────────────────┤
│ ParseSensors│  DataClean  │Reconstruct- │ Representative   │
│             │             │   Single    │      Year        │
└──────┬──────┴──────┬──────┴──────┬──────┴────────┬────────┘
       │             │             │               │
       ▼             ▼             ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                      Reporting 组件                          │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────────────┐  │
│  │ 数据聚合  │  │ 报告生成  │  │      多格式输出          │  │
│  └───────────┘  └───────────┘  └───────────────────────────┘  │
└───────────────────────────┬───────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│     Typst     │  │    Pandoc     │  │     CSV/TXT   │
│   (PDF输出)   │  │  (DOCX输出)   │  │  (数据导出)   │
└───────────────┘  └───────────────┘  └───────────────┘
```

## Python Implementation (cleanmast)

Python implementation provides equivalent report generation through `cleanmast report` commands.

### Report Atom Architecture

The Python implementation uses a modular "atom" architecture for report generation:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Report Command Layer                         │
│            cleanmast report <report-type> --config              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      Report Orchestrator                         │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐  │
│  │  Load Data    │  │  Load Config  │  │  Dispatch Atoms   │  │
│  └───────────────┘  └───────────────┘  └───────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   StatAtom    │  │  TableAtom    │  │   PlotAtom    │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   DocsAtom    │  │   DocsAtom    │  │   DocsAtom    │
└───────────────┘  └───────────────┘  └───────────────┘
```

### Atom Types

| Atom Type | 职责 | 输出 | 说明 |
|-----------|------|------|------|
| **StatAtom** | 统计计算 | Polars DataFrame | 计算风速、风向、湍流等统计指标 |
| **TableAtom** | 表格生成 | Markdown table | 生成规范化的数据表格 |
| **PlotAtom** | 图表生成 | PNG/SVG | 使用 Altair 生成风玫瑰图、时序图等 |
| **DocsAtom** | 文档合成 | Typst source | 使用 typst-py 生成最终报告 |

### Commands

Python version uses `uv run cleanmast report` command structure:

| 命令 | 说明 |
|------|------|
| `uv run cleanmast report clean --config config.toml` | 数据清洗报告 |
| `uv run cleanmast report recovery --config config.toml` | 恢复报告 |
| `uv run cleanmast report reconstruct-single --config config.toml` | 单mast重建报告 |
| `uv run cleanmast report cross-mast --config config.toml` | 跨mast报告 |
| `uv run cleanmast report timeseries --config config.toml` | 时序报告 |
| `uv run cleanmast report representative-year --config config.toml` | 代表年报告 |

#### Command Examples

```bash
# Generate clean report with default settings
uv run cleanmast report clean --config config.toml

# Generate timeseries report for specific mast
uv run cleanmast report timeseries --config config.toml --mast mast1

# Generate all reports
uv run cleanmast report all --config config.toml
```

### Output Structure

```
project/
├── report-masts/
│   ├── clean/
│   │   ├── report.typ
│   │   ├── tables/
│   │   │   └── coverage.csv
│   │   └── plots/
│   │       ├── wind_rose.png
│   │       └── coverage_timeline.png
│   ├── recovery/
│   │   ├── report.typ
│   │   └── plots/
│   ├── reconstruct-single/
│   │   ├── report.typ
│   │   └── plots/
│   ├── timeseries/
│   │   └── [mast-name]/
│   │       ├── report.typ
│   │       ├── wind_rose.png
│   │       └── weibull.png
│   └── representative-year/
│       ├── report.typ
│       └── plots/
```

### Dependencies

#### Python Libraries

| 依赖库 | 用途 | 版本 |
|--------|------|------|
| **altair** | 声明式可视化 | ^5.0 |
| **vl-convert-python** | Vega-Lite 图表导出 | ^1.0 |
| **typst-py** | Typst 文档生成 | ^0.0 |
| **polars** | 数据处理 | ^1.0 |
| **typer** | CLI 框架 | ^0.15 |
| **pydantic** | 配置验证 | ^2.0 |

#### External Tools

| 工具 | 用途 | 安装方式 |
|------|------|----------|
| **typst CLI** | PDF 编译 | `cargo install typst-cli` |
| **typ2docx** | DOCX 转换 | 随项目提供 |

### Differences from Julia

| 特性 | Julia (CleanMast) | Python (cleanmast) |
|------|-------------------|-------------------|
| CLI Framework | Comonicon.jl | Typer |
| DataFrame | DataFrames.jl | Polars |
| Plotting | AlgebraOfGraphics.jl | Altair |
| Report Engine | Typst.jl | typst-py |
| Docx Export | Pandoc | typ2docx |
| Configuration | TOML | TOML + Pydantic |

#### 架构差异

**Julia 实现特点:**

- 原生 Julia 类型系统，强类型约束
- 函数式编程风格，管道操作符支持
- 与 Julia 生态深度集成

**Python 实现特点:**

- Pydantic 模型用于配置验证
- Polars lazy API 用于高性能数据处理
- Altair 声明式可视化语法
- 更符合 Python 生态习惯

#### 数据格式差异

| 格式 | Julia | Python |
|------|-------|--------|
| 中间数据 | Parquet (默认) | Parquet |
| 配置 | TOML | TOML |
| 报告输出 | Typst | Typst |
| 图表 | PNG/SVG | PNG/SVG |
| 数据导出 | CSV | CSV |
