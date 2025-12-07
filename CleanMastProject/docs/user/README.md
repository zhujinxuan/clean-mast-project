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
- `project init` - 创建带有示例配置的新项目
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

1. **初始化项目**：
```bash
julia bin/CleanMast.jl project init projects/my-windfarm
```

2. **准备数据**：将原始数据文件放入项目目录

3. **解析传感器**：
```bash
julia bin/CleanMast.jl project parse-sensors projects/my-windfarm
```

4. **运行完整处理**：
```bash
julia bin/CleanMast.jl process steps --all projects/my-windfarm
```

## 配置

CleanMast 为不同的处理步骤使用 TOML 配置文件：

- `parse-sensors.toml` - 传感器数据解析配置
- `process-clean.toml` - 数据清理规则和参数
- `reconstruct-single.toml` - 单测风塔重构设置
- `train-meso.toml` - 中尺度模型训练配置
- 每个处理步骤都有更多配置文件

配置文件可以使用 `recommend` 命令自动生成。

## 详细文档

- [快速开始教程](quick-start.md) - 完整的入门指南
- [命令参考](commands/) - 详细的命令文档
- [工作流程](workflows/) - 常见处理流程
- [配置指南](configuration/) - 配置文件说明

## 项目结构

```
CleanMast/
├── src/                    # 主要源代码
├── test/                   # 测试套件
├── docs/                   # 文档
├── example_project/        # 示例配置
└── bin/CleanMast.jl       # 主要可执行文件
```

## 支持

如需帮助或反馈：
- 查看详细文档
- 检查示例项目配置
- 联系开发团队