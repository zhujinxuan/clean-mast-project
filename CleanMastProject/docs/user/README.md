# CleanMast 用户指南

## 概览

CleanMast 是一个用于处理风能测风塔数据的 Julia 项目，专门设计用于解析、清理和重构来自气象测风塔 CSV 文件的数据。它提供强大的数据验证、清理规则和重构能力。

## 主要功能

- **灵活的列名解析**：支持可配置格式的数据解析
- **综合数据清理规则**：
  - 传感器数值范围验证
  - 高度间层差检查
  - 结冰检测
  - 塔影检测和校正
- **数据重构能力**：
  - 基于单测风塔相关性的重构
  - 中尺度数据重构
  - 代表年校准
- **命令行界面**：便于集成的命令行工具
- **分析和报告工具**：全面的数据分析和报告生成

## 安装

1. 克隆代码仓库
2. 安装 Julia 1.6 或更高版本
3. 在项目目录中从 Julia REPL 运行：

```julia
using Pkg
Pkg.activate(".")
Pkg.instantiate()
```

## 快速开始

### 基本使用

通过命令行进行基本使用：

```bash
julia bin/CleanMast.jl <命令> <选项>
```

### 主要命令分类

**项目设置**
- `cleanmast init` (Python) - 创建带有示例配置的新项目
- `project parse-sensors` - 将传感器数据解析为结构化格式

**数据处理**
- `process steps --all` - 执行完整的处理流水线
- `process clean` - 应用数据清理规则
- `process tower-shading` - 检测和校正塔影效应
- `process reconstruct-single` - 使用单测风塔相关性重构
- `process train-meso` - 训练中尺度相关模型
- `process reconstruct-meso` - 使用中尺度数据重构
- `process representative-year` - 校准到代表性条件

**配置管理**
- `recommend <过程>` - 为每个处理步骤生成配置文件

**分析和报告**
- `report all` - 生成所有类型报告
- `report clean` - 数据清理质量报告
- `report timeseries` - 综合风能分析和报告
- `report recovery` - 数据恢复分析报告
- `report representative-year` - 代表年校正报告
- `report cross-mast` - 跨塔相关性分析报告
- `report reconstruct-single` - 单塔重构质量报告

### 典型工作流程

#### 1. 初始化项目

```bash
uv run cleanmast init projects/my-windfarm
```

#### 2. 准备数据文件

##### 测风塔数据预处理

原始测风塔数据需要先放入 `pre-masts/` 进行预处理，再输出到 `masts/`：

1. 为每个测风塔创建目录并放入原始文件：

```nu
# 创建测风塔目录
mkdir projects/my-windfarm/pre-masts/M01

# 将原始数据放入对应目录（激光雷达目录名需以 L 开头，如 L01）
mv tower1-*.txt projects/my-windfarm/pre-masts/M01/
```

2. 使用 Claude Code 的 `preprocess-mast-data` skill 进行预处理：

```
请预处理 projects/my-windfarm/pre-masts/M01 的数据，使用 preprocess-mast-data skill
```

Claude Code 会调用 skill 自动完成：
- 检查原始数据格式和一致性
- 生成合并配置（`csv-merger.toml`）和格式转换配置（`nrg-format.toml`）
- 执行 CSV 合并和 NRG 标准格式转换
- 输出最终文件到 `masts/M01.csv`

##### 中尺度数据

中尺度数据直接放入 `mesos/` 目录：

```nu
mv era5-tower1.txt projects/my-windfarm/mesos/
mv era5-tower2.txt projects/my-windfarm/mesos/
```

#### 3. 生成解析配置

```nu
julia bin/CleanMast.jl recommend parse-sensors projects/my-windfarm
```

#### 4. 解析原始数据

```nu
julia bin/CleanMast.jl project parse-sensors.toml projects/my-windfarm
```

#### 5. 运行完整处理

```nu
julia bin/CleanMast.jl process steps --all projects/my-windfarm
```

这将依次执行所有 18 个处理步骤：
- 步骤 1-2: 数据清理配置和执行
- 步骤 3-4: 塔影校正配置和执行
- 步骤 5-6: 单塔重构配置和执行
- 步骤 7-10: 跨塔模型训练和重构
- 步骤 11-14: 中尺度模型训练和重构
- 步骤 15-16: 代表年校准
- 步骤 17-18: 风机时间序列生成

##### 灵活的步骤控制

如果需要分步骤执行或调试特定环节：

```nu
# 查看所有可用步骤
julia bin/CleanMast.jl process steps --list

# 仅执行数据准备步骤 (1-6)
julia bin/CleanMast.jl process steps --from 1 --to 6 projects/my-windfarm

# 从步骤 10 开始执行到结束
julia bin/CleanMast.jl process steps --from 10 projects/my-windfarm

# 仅执行中尺度相关步骤 (11-14)
julia bin/CleanMast.jl process steps --from 11 --to 14 projects/my-windfarm
```

#### 6. 生成报告配置

```nu
julia bin/CleanMast.jl recommend report-all projects/my-windfarm
```

#### 7. 生成分析报告

```nu
julia bin/CleanMast.jl report all projects/my-windfarm
```

#### 8. 查看报告

使用 Typst 编译查看报告：

```nu
# 进入报告目录
cd projects/my-windfarm/report-masts

# 编译并查看报告（具体报告文件名以生成结果为准）
typst compile data-quality-report.typ data-quality-report.pdf
```

### 输出结果

处理完成后，您将获得：

- **原始数据** (`raw/`) - 标准化后的时间序列数据
- **清理数据** (`clean/`) - 去除异常值后的数据
- **重构数据** (`reconstruct-meso/`) - 完整的长期数据序列
- **分析报告** (`report-masts/`) - 专业的风资源评估报告

## 配置

CleanMast 为不同的处理步骤使用 TOML 配置文件：

- `parse-sensors.toml` - 传感器数据解析配置
- `process-clean.toml` - 数据清理规则和参数
- `reconstruct-single.toml` - 单测风塔重构设置
- `train-meso.toml` - 中尺度模型训练配置
- 每个处理步骤都有更多配置文件

配置文件可以使用 `recommend` 命令自动生成。

## 详细文档

- [命令参考](commands/) - 详细的命令文档
- [配置指南](configuration/) - 配置文件说明

## 项目结构

```
clean-mast-project/
├── CleanMastProject/       # Julia 实现
│   ├── src/                # 主要源代码
│   ├── test/               # 测试套件
│   └── docs/               # 文档
├── packages/cleanmast/     # Python 实现
│   └── src/cleanmast/
│       └── scaffold/       # 项目初始化模板
└── bin/CleanMast.jl        # Julia 入口
```

## 支持

如需帮助或反馈：
- 查看详细文档
- 检查示例项目配置
- 联系开发团队