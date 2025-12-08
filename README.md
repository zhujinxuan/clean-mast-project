# CleanMast

Wind energy meteorological tower data processing toolkit.

## 🚧 Migration Status

This project is currently being migrated from Julia to Python.

- **Julia (Current - Stable)**: Full-featured, production-ready
- **Python (In Development)**: Preprocessing tools available, main features in progress

See [Migration Status](docs/migration/status.md) for details.

---

CleanMast 是一个用于处理风能测风塔数据的项目，专门设计用于解析、清理和重构来自气象测风塔 CSV 文件的数据。它提供强大的数据验证、清理规则和重构能力。

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

### Julia Version (生产环境推荐)

1. 克隆代码仓库
2. 安装 Julia 1.11.7 或更高版本
3. 在项目目录中从 Julia REPL 运行：

```julia
using Pkg
Pkg.activate(".")
Pkg.instantiate()
```

### Python Version (开发中)

1. 安装 Python 3.11 或更高版本
2. 安装 [uv](https://github.com/astral-sh/uv)
3. 从项目根目录运行：

```bash
uv sync
```

Python 版本包含：
- ✅ **preprocess-tools**: 数据预处理工具（可用）
- 🚧 **cleanmast**: 主分析工具包（开发中）

## 使用方法

### Julia Version

通过命令行进行基本使用：

```bash
julia bin/CleanMast.jl <命令> <选项>
```

对于一般使用者，见 [CleanMastProject/docs/](CleanMastProject/docs/)

### Python Version

```bash
# Preprocessing tools (unified CLI)
uv run preprocess csv-merge config.toml
uv run preprocess col-normalizer config.toml
uv run preprocess type-normalizer config.toml
uv run preprocess timestamp config.toml

# CleanMast (coming soon)
uv run cleanmast parse-sensors --config config.toml
uv run cleanmast process --config config.toml
```

See [packages/preprocess-tools/README.md](packages/preprocess-tools/README.md) for preprocessing documentation.

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

### 📖 Documentation Navigation

- **[Documentation Hub](docs/README.md)** - 文档导航中心

### Julia Documentation (Current Production)

CleanMast Julia 版本提供三层文档结构：

- **📚 用户文档**: [CleanMastProject/docs/user/](CleanMastProject/docs/user/)
- **💻 技术文档**: [CleanMastProject/docs/technical/](CleanMastProject/docs/technical/)
- **💻 开发文档**: [CleanMastProject/docs/development/](CleanMastProject/docs/development/)

### Python Documentation (In Development)

- **[Migration Status](docs/migration/status.md)** - 迁移状态
- **[Migration Guide](docs/migration/julia-to-python.md)** - Julia → Python 迁移指南
- **[Preprocess Tools](docs/python/preprocess-tools/)** - 预处理工具文档
- **[CleanMast Python](docs/python/cleanmast/)** - Python 版本文档（开发中）

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
clean-mast-project/
├── Project.toml               # Julia workspace
├── pyproject.toml             # Python workspace
│
├── CleanMastProject/          # Julia implementation (production)
│   ├── src/                   # 主要源代码
│   ├── test/                  # 测试套件
│   └── docs/                  # Julia 文档
│
├── packages/                  # Python implementation (in development)
│   ├── preprocess-tools/      # 数据预处理工具
│   │   ├── src/preprocess_tools/
│   │   ├── tests/
│   │   └── docs/
│   └── cleanmast/             # 主分析工具包
│       ├── src/cleanmast/
│       │   ├── types/         # 核心类型定义
│       │   ├── parse_sensors/ # 数据解析和列映射
│       │   ├── process/       # 数据清理规则
│       │   ├── reconstruct/   # 数据重构
│       │   ├── analyze/       # 分析模块
│       │   └── reports/       # 报告生成
│       ├── tests/
│       └── docs/
│
├── docs/                      # 共享文档
│   ├── migration/             # 迁移指南
│   └── python/                # Python 文档
│
├── projects/                  # 项目数据
└── bin/                       # 可执行文件
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