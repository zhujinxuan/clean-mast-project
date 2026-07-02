# CleanMast

Wind energy meteorological tower data processing toolkit.

## 工作流程

CleanMast 的数据处理分为两个阶段：

### 第一阶段：数据预处理（AI Agent）

原始测风塔数据格式各异（NRG logger、Lidar、CSV 导出等），需要先转换为 CleanMast 能消费的标准格式。这一步由 AI Agent 通过 `cleanmast-preprocess` skill 完成：

1. AI 检查原始数据格式（分隔符、编码、列名、时间戳格式）
2. 运行 `uv run preprocess csv-merge` 合并多个数据文件
3. 运行 `uv run preprocess col-normalizer` 标准化列名
4. 运行 `uv run preprocess type-normalizer` 转换数据类型
5. 输出标准化的 CSV 文件到 `masts/` 目录

预处理完成后，数据已准备好供 CleanMast 消费（无论 Julia 还是 Python）。

### 第二阶段：实验运行（Justfile）

预处理完成后，在实验目录中通过 Justfile 执行完整的处理流水线：

```bash
# 初始化实验目录
mise run init:experiment projects/my-windfarm

# 进入实验目录
cd projects/my-windfarm

# 运行完整流水线
just run-all
```

## 项目状态

CleanMast 项目同时使用 Julia 和 Python 两种运行时。Julia 负责数据处理流水线（步骤 1-16），Python 负责高度填充、风机时间序列和报告生成。`mise run bootstrap` 安装所有依赖。

**安装依赖**：`mise run bootstrap`（需要先安装 [mise](https://mise.jdx.dev/)）
**创建实验**：`mise run init:experiment projects/<name>` → `cd projects/<name>` → `just run-all`
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

1. 安装 [mise](https://mise.jdx.dev/)（版本管理工具）
2. 克隆代码仓库
3. 从项目根目录运行：

```bash
mise run bootstrap
```

此命令会自动安装 Julia 和 Python 的所有依赖。

包含的工具：
- ✅ **preprocess-tools**: 数据预处理工具（csv-merge、col-normalizer、type-normalizer、timestamp）
- ✅ **cleanmast**: 主分析工具包
  - ✅ `fill-heights` - 高度填充
  - ✅ `report` - 报告生成

## 使用方法

### 创建项目并运行

```bash
# 1. 初始化实验目录（创建 Justfile 和目录结构）
mise run init:experiment projects/my-windfarm

# 2. 进入实验目录
cd projects/my-windfarm

# 3. 运行完整流水线
just run-all

# 4. 或运行单个步骤
just process-clean
just report-timeseries
```

### 查看可用命令

```bash
cd projects/my-windfarm
just --list
```

### Justfile 主要 Recipe

**项目设置**
- `just recommend-parse-sensors` - 生成传感器解析配置
- `just parse-sensors` - 解析传感器数据

**数据处理**
- `just process-clean` - 应用数据清理规则
- `just process-tower-shading` - 检测和校正塔影效应
- `just process-reconstruct-single` - 单测风塔相关性重构
- `just process-train-meso` - 训练中尺度相关模型
- `just process-reconstruct-meso` - 中尺度数据重构
- `just process-representative-year` - 代表年校准

**高度填充与报告（Python）**
- `just recommend-fill-heights` - 生成高度填充配置
- `just fill-heights-meso` - 执行高度填充
- `just recommend-report-config` - 生成报告配置
- `just report-timeseries` - 生成时间序列报告

**便捷流水线**
- `just run-all` - 完整流水线（推荐配置 → 解析 → 处理 → 填充 → 报告）

### 独立 Python 命令

```bash
# 预处理工具（第一阶段）
uv run preprocess csv-merge config.toml
uv run preprocess col-normalizer config.toml
uv run preprocess type-normalizer config.toml

# 项目管理
mise run init:experiment projects/my-windfarm
uv run cleanmast recommend fill-heights projects/my-windfarm/
```

See [packages/preprocess-tools/README.md](packages/preprocess-tools/README.md) for preprocessing documentation.

## 配置

CleanMast 使用 TOML 配置文件来控制不同的处理步骤。配置文件由 `recommend` 或 `just recommend-*` 命令自动生成，用户也可手动编辑。

## 文档

- **[Documentation Hub](docs/README.md)** - 文档导航中心
- **[Quick Start](CleanMastProject/docs/user-guide/quickstart.md)** - 快速入门
- **[Complete Pipeline](CleanMastProject/docs/user-guide/workflow/complete-pipeline.md)** - 完整流水线
- **[Migration Status](docs/migration/status.md)** - 迁移状态
- **[Preprocess Tools](docs/python/preprocess-tools/)** - 预处理工具文档
- **[CleanMast Python](docs/python/cleanmast/)** - Python 版本文档
- **[Julia Docs](CleanMastProject/docs/)** - Julia 实现文档


## 项目结构

```
clean-mast-project/
├── mise.toml                 # mise 配置（bootstrap 任务）
├── Project.toml               # Julia workspace
├── pyproject.toml             # Python workspace
│
├── CleanMastProject/          # Julia 实现
│   ├── src/                   # 主要源代码
│   ├── test/                  # 测试套件
│   └── docs/                  # 文档
│
├── packages/                  # Python 包
│   ├── preprocess-tools/      # 数据预处理工具
│   ├── cleanmast/             # 主分析工具包
│   │   └── scaffold/          # 项目模板（Justfile 等）
│   └── typst_ir/              # Typst IR 文档处理库
│
├── docs/                      # 共享文档
├── projects/                  # 项目目录（每个项目含 Justfile）
└── bin/                       # 可执行文件
```

## 开发状态

**已完成：**
- ✓ 模块化 CLI，支持命令分类
- ✓ 配置解析和验证
- ✓ 灵活的传感器数据解析
- ✓ 基本数据清理规则（范围、层差、结冰）
- ✓ 单测风塔重构（基本算法）
- ✓ 中尺度数据训练和重构
- ✓ 代表年校准
- ✓ 塔影检测和校正
- ✓ 高度填充（fill-heights）- Python
- ✓ 时间序列报告生成 - Python
- ✓ Justfile 项目模板和流水线编排

**进行中：**
- Python 迁移剩余模块（parse-sensors、data-clean、reconstruction）
- 跨测风塔重构算法（`reconstruct-cross`）
- 大数据集的性能优化


## 贡献

1. 遵循项目规则中定义的函数式编程风格
2. 包含类型规范
3. 为新功能添加单元测试
4. 使用文档字符串编写文档
5. 提交带有清晰描述的PR

更多详细信息请参考[开发文档](docs/development/)。

## 许可证

MIT License