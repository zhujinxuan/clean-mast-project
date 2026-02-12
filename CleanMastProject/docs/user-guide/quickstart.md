# CleanMast 快速入门指南

本指南将帮助您在 15 分钟内完成从零到首次处理测风塔数据的完整流程。无论您是风能工程师还是数据分析师，都能通过以下步骤快速上手 CleanMast。

## 1. 环境准备

在开始之前，请确保您的系统满足以下要求。CleanMast 提供 Julia 和 Python 两种运行方式，您可以根据项目需求选择其一。

### 系统要求

**通用要求：**
- 操作系统：Windows 10/11、macOS 10.15+ 或 Linux（Ubuntu 20.04+）
- 内存：最低 8GB，推荐 16GB 以上
- 磁盘空间：至少 2GB 可用空间
- 网络：用于下载依赖包

**Julia 版本要求：**
- Julia 1.6.0 或更高版本（推荐 1.9.x）
- 可从 [julialang.org](https://julialang.org/downloads/) 下载安装

**Python 版本要求：**
- Python 3.10 或更高版本
- uv 包管理器（推荐安装方式）

### 安装 uv 包管理器（Python 路径）

如果您选择使用 Python 版本，建议通过 uv 进行安装。uv 是一个高性能的 Python 包管理器，能够快速处理依赖。

```bash
# 使用 pip 安装
pip install uv

# 或使用 cargo 安装（需要 Rust）
cargo install uv
```

### 验证安装

安装完成后，请验证环境是否正确配置。

**Julia 验证：**
```bash
julia --version
```
应显示 Julia 版本号，例如：`julia version 1.9.4`。

**Python 验证：**
```bash
python --version
uv --version
```
应分别显示 Python 和 uv 版本号。

## 2. 安装 CleanMast

根据您的使用场景，选择 Julia 或 Python 版本进行安装。Julia 版本功能完整，适合生产环境；Python 版本正在开发中，适合尝鲜用户。

### Julia 版本安装（推荐）

CleanMast 使用 Julia workspace 结构，源代码位于 `CleanMastProject/` 子目录中。

**步骤 1：克隆代码仓库**

```bash
git clone https://github.com/your-repo/clean-mast-project.git
cd clean-mast-project
```

**步骤 2：激活项目环境并安装依赖**

```bash
julia
```

在 Julia REPL 中执行：

```julia
using Pkg
Pkg.activate("CleanMastProject")
Pkg.instantiate()
```

首次运行会自动下载并安装所有依赖包，包括 DataFrames.jl、CSV.jl、GLM.jl 等。根据网络情况，此过程可能需要 5-15 分钟。

**步骤 3：验证安装**

```bash
julia bin/CleanMast.jl --help
```

如果显示命令帮助信息，说明安装成功。

### Python 版本安装

Python 版本目前包含预处理工具，主分析功能正在开发中。

**步骤 1：克隆代码仓库**

```bash
git clone https://github.com/your-repo/clean-mast-project.git
cd clean-mast-project
```

**步骤 2：同步依赖**

```bash
uv sync
```

此命令会创建虚拟环境并安装所有依赖。

**步骤 3：验证安装**

```bash
uv run cleanmast --help
```

## 3. 创建第一个项目

安装完成后，让我们创建第一个测风数据处理项目。CleanMast 使用项目目录来管理所有配置、数据和输出结果。

### 使用 Python 命令初始化

```bash
uv run cleanmast init projects/my-first-project
```

此命令会在 `projects/` 目录下创建一个名为 `my-first-project` 的新项目，包含以下目录结构：

```
projects/my-first-project/
├── pre-masts/          # 原始测风塔数据（预处理前）
├── masts/              # 处理后的测风塔数据
├── mesos/              # 中尺度数据
├── raw/                # 解析后的原始数据
├── clean/              # 清理后的数据
├── reconstruct-meso/  # 中尺度重构数据
├── reconstruct-cross/ # 跨塔重构数据
├── report-masts/       # 分析报告
└── config/             # 配置文件目录
```

### 目录说明

| 目录 | 用途 |
|------|------|
| `pre-masts/` | 存放原始测风塔数据文件（CSV/TXT） |
| `masts/` | 预处理后的标准化测风塔数据 |
| `mesos/` | 中尺度模型数据（如 ERA5） |
| `raw/` | 解析后的时间序列数据 |
| `clean/` | 经过质量控制的数据 |
| `reconstruct-meso/` | 中尺度重构后的完整数据序列 |
| `report-masts/` | 生成的 PDF 分析报告 |

## 4. 准备数据

CleanMast 处理的是标准化后的测风塔数据。如果您的原始数据需要预处理，请按以下步骤操作。

### 放置原始数据

将您的原始测风塔数据文件放入对应目录：

```bash
# 创建测风塔目录（以 M01 为例）
mkdir projects/my-first-project/pre-masts/M01

# 将原始文件放入目录
cp /path/to/your/tower-data.csv projects/my-first-project/pre-masts/M01/
```

**数据格式要求：**
- 支持 CSV、TXT 格式
- 必须包含时间戳列（如 `timestamp`、`datetime`）
- 必须包含风速、风向传感器数据列
- 推荐使用 10 分钟平均数据

### 数据预处理（如需要）

如果原始数据需要格式转换或合并，可使用预处理工具：

```bash
# CSV 文件合并
uv run preprocess csv-merge config.toml

# 列名标准化
uv run preprocess col-normalizer config.toml

# 时间戳处理
uv run preprocess timestamp config.toml
```

详细的预处理配置说明请参考[预处理工具文档](../python/preprocess-tools/)。

## 5. 运行数据处理

数据准备完成后，即可运行完整的处理流水线。CleanMast 会依次执行数据解析、质量控制、塔影校正、数据重构等步骤。

### 生成配置文件

首先，使用 `recommend` 命令生成各处理步骤的配置文件：

```bash
julia bin/CleanMast.jl recommend parse-sensors projects/my-first-project
```

此命令会在 `projects/my-first-project/config/` 目录下生成 `parse-sensors.toml` 文件，包含传感器列映射配置。

### 解析传感器数据

```bash
julia bin/CleanMast.jl project parse-sensors.toml projects/my-first-project
```

此命令会解析 `masts/` 目录下的数据文件，将传感器列名与内部标准名称进行映射，输出到 `raw/` 目录。

### 执行完整处理流水线

运行所有 18 个处理步骤：

```bash
julia bin/CleanMast.jl process steps --all projects/my-first-project
```

**流水线包含的步骤：**

| 步骤范围 | 处理内容 |
|----------|----------|
| 步骤 1-2 | 数据清理配置和执行 |
| 步骤 3-4 | 塔影校正配置和执行 |
| 步骤 5-6 | 单塔重构配置和执行 |
| 步骤 7-10 | 跨塔模型训练和重构 |
| 步骤 11-14 | 中尺度模型训练和重构 |
| 步骤 15-16 | 代表年校准 |
| 步骤 17-18 | 风机时间序列生成 |

### 分步执行（如需要）

如需调试特定环节，可指定步骤范围：

```bash
# 仅执行数据清理步骤
julia bin/CleanMast.jl process steps --from 1 --to 2 projects/my-first-project

# 仅执行中尺度相关步骤
julia bin/CleanMast.jl process steps --from 11 --to 14 projects/my-first-project
```

## 6. 生成分析报告

数据处理完成后，可以生成专业的风资源评估报告。

### 生成报告配置

```bash
julia bin/CleanMast.jl recommend report-all projects/my-first-project
```

此命令会在配置目录生成报告相关的配置文件。

### 生成全部报告

```bash
julia bin/CleanMast.jl report all projects/my-first-project
```

**可生成的报告类型：**

| 报告类型 | 说明 |
|----------|------|
| 数据质量报告 | 展示原始数据的完整性和质量指标 |
| 清理质量报告 | 分析数据清理效果和异常值分布 |
| 重构质量报告 | 评估数据重构的准确性和可靠性 |
| 代表年报告 | 展示长期校准后的代表性数据 |
| 时间序列报告 | 综合风资源分析和统计摘要 |

## 7. 验证处理结果

处理完成后，请按以下步骤验证结果是否正确。

### 检查输出目录

```bash
# 查看生成的数据文件
ls -la projects/my-first-project/clean/
ls -la projects/my-first-project/reconstruct-meso/

# 查看生成的报告
ls -la projects/my-first-project/report-masts/
```

**预期输出文件：**

| 目录 | 预期文件 |
|------|----------|
| `raw/` | `M01_raw.parquet` 等解析数据 |
| `clean/` | `M01_clean.parquet` 等清理数据 |
| `reconstruct-meso/` | `M01_reconstruct-meso.parquet` 等重构数据 |
| `report-masts/` | `data-quality-report.pdf` 等分析报告 |

### 验证报告内容

使用 PDF 阅读器打开生成的报告，检查以下内容：

- **数据摘要**：时间范围、数据点数、缺失率
- **质量指标**：数据完整率、有效数据比例
- **统计分析**：平均风速、风向分布、湍流强度
- **图表**：风玫瑰图、时间序列图、高度剖面图

### 常见验证项

1. **时间范围**：确认数据覆盖您期望的时间段
2. **数据完整性**：缺失数据比例是否在合理范围内（通常 < 10%）
3. **风速范围**：确认风速值在 0-50 m/s 范围内
4. **风向范围**：确认风向值在 0-360 度范围内

## 8. 下一步学习

您已成功完成第一次 CleanMast 数据处理！以下是后续学习建议。

### 深入学习主题

| 主题 | 说明 | 参考文档 |
|------|------|----------|
| 命令详解 | 了解每个命令的详细用法和参数 | [命令参考](../user/commands/) |
| 配置指南 | 自定义各处理步骤的参数 | [配置指南](../user/configuration/) |
| 塔影校正 | 了解塔影效应的检测和校正原理 | [塔影校正](../user/commands/process/tower-shading.md) |
| 中尺度重构 | 学习如何使用 ERA5 等中尺度数据 | [中尺度重构](../user/commands/process/reconstruct-meso.md) |
| 代表年校准 | 了解长期数据校准方法 | [代表年校准](../user/commands/process/representative-year.md) |

### 探索示例项目

参考 `projects/pn-masts/` 目录下的完整示例项目，学习专业用户如何配置和使用 CleanMast。

### 常见问题

如遇到问题，请先查阅以下资源：

- [命令文档](../user/commands/) - 详细的命令说明
- [配置文档](../user/configuration/) - 配置文件参数详解
- [项目 README](../user/README.md) - 完整用户指南

## 9. 快速参考

以下是本指南中使用的关键命令速查表。

### 常用命令速查

```bash
# 初始化项目
uv run cleanmast init projects/my-project

# 生成配置
julia bin/CleanMast.jl recommend parse-sensors projects/my-project

# 解析数据
julia bin/CleanMast.jl project parse-sensors.toml projects/my-project

# 执行处理
julia bin/CleanMast.jl process steps --all projects/my-project

# 生成报告
julia bin/CleanMast.jl recommend report-all projects/my-project
julia bin/CleanMast.jl report all projects/my-project
```

### 目录结构速览

```
projects/my-project/
├── pre-masts/     # 原始数据
├── masts/         # 标准化数据
├── mesos/         # 中尺度数据
├── raw/           # 解析输出
├── clean/         # 清理输出
└── report-masts/  # 报告输出
```

---

恭喜您完成 CleanMast 快速入门！如需更多帮助，请参阅详细文档或联系技术支持。
