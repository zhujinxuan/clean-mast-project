# CleanMast

CleanMast 是一个用于处理风能测风塔数据的 Julia 项目，专门设计用于解析、清理和重构来自气象测风塔 CSV 文件的数据。它提供强大的数据验证、清理规则和重构能力。

## 主要功能

- 灵活的列名解析，支持可配置格式
- 综合数据清理规则：
  - 传感器数值范围验证
  - 高度间层差检查
  - 结冰检测
  - 塔影检测和校正
- 数据重构能力：
  - 基于单测风塔相关性的重构
  - 中尺度数据重构
  - 代表年校准
- 命令行接口，便于集成
- 分析和报告工具

## 安装

1. 克隆代码仓库
2. 安装 Julia 1.11.7 或更高版本
3. 在项目目录中从 Julia REPL 运行：

```julia
using Pkg
Pkg.activate(".")
Pkg.instantiate()
```

## 使用方法

通过命令行进行基本使用：

```bash
julia bin/CleanMast.jl <命令> <选项>
```

对于一般使用者，见 [docs/user/quick-start.md](docs/user/quick-start.md)

### 主要命令分类

**项目设置**
- `project init` - 创建带有示例配置的新项目
- `project parse-sensors` - 将传感器数据解析为 csv 和对应的传感器描述 toml 文件

**数据处理**
- `process steps --all` - 执行完整的处理流水线(包含生成各步骤配置文件)
- `process steps --from X --to Y` - 执行指定范围的处理步骤（灵活控制）
- `process clean` - 应用数据清理规则
- `process tower-shading` - 检测和校正塔影效应
- `process reconstruct-single` - 使用单测风塔相关性重构
- `process train-meso` - 训练中尺度相关模型
- `process reconstruct-meso` - 使用中尺度数据重构
- `process representative-year` - 校准到代表性条件
- `process wt-timeseries` - 生成为 Meteodyn WT 使用的时间序列 csv

**配置管理**
- `recommend <过程>` - 为每个处理步骤生成配置文件

**分析和报告**
- `report all` - 综合风能分析和报告(需先运行 `process steps --all` 和 `recommend report-all`)
- `analyze en` - 土木工程EN标准分析(未完成)

## 文档

CleanMast 提供三层文档结构，面向不同的用户群体：

### 📚 用户文档 (docs/user/)
面向系统用户和风能工程师：
- [快速开始](docs/user/quick-start.md) - 完整的入门教程
- [命令参考](docs/user/commands/) - 详细的命令文档
- [配置指南](docs/user/configuration/) - 配置文件说明

### 💻 技术文档 (docs/technical/)
面向技术专家：
- [算法实现](docs/technical/algorithms/) - 数据处理算法的具体实现细节

### 💻 开发文档 (docs/development/)
面向开发者和贡献者：
- [系统架构](docs/development/architecture/) - 代码结构和设计
- [贡献指南](docs/development/contribution/) - 开发环境和规范
- [API 文档](docs/development/api/) - 核心接口和类型
- [部署指南](docs/development/deployment/) - 构建和发布

## 配置

CleanMast 使用 TOML 配置文件来控制不同的处理步骤：

- `parse-sensors.toml` - 传感器数据解析配置
- `process-clean.toml` - 数据清理规则和参数
- `reconstruct-single.toml` - 单测风塔重构设置
- `train-meso.toml` - 中尺度模型训练配置
- 各个处理步骤都有对应的配置文件

配置文件可以使用 `recommend` 命令自动生成。

## 项目结构

```
CleanMast/
├── src/                    # 主要源代码
│   ├── CleanMastCli.jl   # 命令行接口
│   ├── Types/            # 核心类型定义
│   ├── ParseSensors/     # 数据解析和列映射
│   ├── DataClean/        # 数据清理规则和处理
│   ├── ReconstructSingleMast/ # 单测风塔重构
│   ├── ReconstructMeso/  # 中尺度重构
│   ├── AnalyzeTimeSeries/ # 分析和报告
│   └── ...               # 其他处理模块
├── test/               # 测试套件
├── docs/               # 详细文档
│   ├── user/           # 用户文档
│   ├── scientific/     # 科学文档
│   └── development/    # 开发文档
├── example_project/    # 示例配置
└── bin/CleanMast.jl   # 主要可执行文件
```

## 开发状态

**已完成：**
- ✓ 模块化CLI，支持命令分类
- ✓ 配置解析和验证
- ✓ 灵活的传感器数据解析
- ✓ 基本数据清理规则（范围、层差、结冰）
- ✓ 单测风塔重构（基本算法）
- ✓ 中尺度数据训练和重构
- ✓ 代表年校准
- ✓ 塔影检测和校正
- ✓ 分析和报告能力
- ✓ 广泛的测试覆盖

**进行中：**
- 跨所有处理阶段的数据覆盖分析
- 跨测风塔重构算法（`reconstruct-cross`）
- 测风塔与中尺度数据源间的相关性分析
- 增强的单测风塔重构策略
- 大数据集的性能优化

**计划功能：**
- LiDAR特定的数据清理规则
- 使用LLM提示的AI辅助传感器解析
- 基于相关性分析的自动中尺度源选择
- 增强的可视化能力
- 其他分析模块

## 贡献

1. 遵循项目规则中定义的函数式编程风格
2. 包含类型规范
3. 为新功能添加单元测试
4. 使用文档字符串编写文档
5. 提交带有清晰描述的PR

更多详细信息请参考[开发文档](docs/development/)。

## 许可证

MIT License