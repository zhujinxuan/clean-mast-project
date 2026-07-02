# CleanMast 快速入门指南

本指南将帮助您在 15 分钟内完成从零到首次处理测风塔数据的完整流程。无论您是风能工程师还是数据分析师，都能通过以下步骤快速上手 CleanMast。

## 1. 环境准备

在开始之前，请确保您的系统满足以下要求。

### 系统要求

- 操作系统：Windows 10/11、macOS 10.15+ 或 Linux（Ubuntu 20.04+）
- 内存：最低 8GB，推荐 16GB 以上
- 磁盘空间：至少 2GB 可用空间
- 网络：用于下载依赖包

### 安装 mise

CleanMast 使用 [mise](https://mise.jdx.dev/) 作为版本管理工具，统一管理 Julia 和 Python 依赖。

```bash
# macOS / Linux
curl https://mise.run | sh

# Windows (PowerShell)
winget install jdx mise
```

安装完成后，重启终端并验证：

```bash
mise --version
```

## 2. 安装 CleanMast

```bash
# 克隆代码仓库
git clone https://github.com/your-repo/clean-mast-project.git
cd clean-mast-project

# 安装所有依赖（Julia + Python）
mise run bootstrap
```

`mise run bootstrap` 会自动安装 Julia 和 Python 的所有依赖包。首次运行可能需要 5-15 分钟。

## 3. 创建第一个项目

安装完成后，让我们创建第一个测风数据处理项目。

```bash
# 初始化项目（创建 Justfile 和目录结构）
mise run init:experiment projects/my-first-project

# 进入项目目录
cd projects/my-first-project

# 查看可用命令
just --list
```

此命令会在 `projects/` 目录下创建一个新项目，包含 Justfile 和以下目录结构：

```
projects/my-first-project/
├── Justfile              # 项目命令（just --list 查看）
├── pre-masts/            # 原始测风塔数据（预处理前）
├── masts/                # 处理后的测风塔数据
├── mesos/                # 中尺度数据
├── raw/                  # 解析后的原始数据
├── clean/                # 清理后的数据
├── reconstruct-meso/     # 中尺度重构数据
└── rep-ts/               # 报告输出
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
| `rep-ts/` | 生成的报告文件（PDF/DOCX/Typst） |

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
uv run preprocess csv-merge config.toml
uv run preprocess col-normalizer config.toml
uv run preprocess timestamp config.toml
```

详细的预处理配置说明请参考[预处理工具文档](../python/preprocess-tools/)。

## 5. 运行数据处理

数据准备完成后，即可运行完整的处理流水线。所有命令都通过 Justfile 执行。

```bash
# 进入项目目录
cd projects/my-first-project
```

### 生成配置文件并解析传感器数据

```bash
# 生成传感器解析配置
just recommend-parse-sensors

# 解析传感器数据
just parse-sensors
```

### 执行完整处理流水线

运行所有处理步骤（推荐配置 → 清理 → 塔影 → 重构 → 填充 → 报告）：

```bash
just run-all
```

### 分步执行（如需要）

如需调试特定环节，可运行单个步骤：

```bash
# 仅执行数据清理
just process-clean

# 仅执行塔影校正
just process-tower-shading

# 仅执行单塔重构
just process-reconstruct-single

# 仅执行中尺度训练和重构
just process-train-meso
just process-reconstruct-meso

# 仅执行代表年校准
just process-representative-year
```

**流水线包含的步骤：**

| 步骤范围 | 处理内容 | Justfile Recipe |
|----------|----------|-----------------|
| 步骤 1-2 | 数据清理 | `just process-clean` |
| 步骤 3-4 | 塔影校正 | `just process-tower-shading` |
| 步骤 5-6 | 单塔重构 | `just process-reconstruct-single` |
| 步骤 7-10 | 跨塔模型训练和重构 | `just process-train-cross` / `just process-reconstruct-cross` |
| 步骤 11-14 | 中尺度模型训练和重构 | `just process-train-meso` / `just process-reconstruct-meso` |
| 步骤 15-16 | 代表年校准 | `just process-representative-year` |
| 高度填充 | 风速高度外推（Python） | `just fill-heights-meso` |
| 报告生成 | 时间序列报告（Python） | `just report-timeseries` |

## 6. 生成分析报告

数据处理完成后，可以生成专业的风资源评估报告。

```bash
# 生成报告配置
just recommend-report-config

# 生成时间序列报告（PDF/DOCX/Typst）
just report-timeseries
```

**可生成的报告类型：**

| 报告类型 | 说明 |
|----------|------|
| 时间序列报告 | 综合风资源分析和统计摘要 |
| 数据质量报告 | 展示原始数据的完整性和质量指标 |
| 清理质量报告 | 分析数据清理效果和异常值分布 |
| 重构质量报告 | 评估数据重构的准确性和可靠性 |

## 7. 验证处理结果

处理完成后，请按以下步骤验证结果是否正确。

### 检查输出目录

```bash
# 查看生成的数据文件
ls projects/my-first-project/clean/
ls projects/my-first-project/reconstruct-meso/

# 查看生成的报告
ls projects/my-first-project/rep-ts/
```

**预期输出文件：**

| 目录 | 预期文件 |
|------|----------|
| `raw/` | `M01.csv` 等解析数据 |
| `clean/` | `M01.csv` 等清理数据 |
| `reconstruct-meso/` | `M01.csv` 等重构数据 |
| `rep-ts/` | `report.pdf` 等分析报告 |

### 验证报告内容

使用 PDF 阅读器打开生成的报告，检查以下内容：

- **数据摘要**：时间范围、数据点数、缺失率
- **质量指标**：数据完整率、有效数据比例
- **统计分析**：平均风速、风向分布、湍流强度
- **图表**：风玫瑰图、时间序列图、高度剖面图

## 8. 下一步学习

您已成功完成第一次 CleanMast 数据处理！以下是后续学习建议。

### 深入学习主题

| 主题 | 说明 | 参考文档 |
|------|------|----------|
| 命令详解 | 了解每个 Justfile recipe 的详细用法 | [命令参考](../user/commands/) |
| 配置指南 | 自定义各处理步骤的参数 | [配置指南](../user/configuration/) |
| 完整流水线 | 了解 18 步流水线的详细流程 | [完整流水线](workflow/complete-pipeline.md) |
| 预处理工具 | 数据预处理工作流 | [预处理工作流](workflow/preprocessing.md) |

### 常见问题

如遇到问题，请先查阅以下资源：

- [故障排除指南](workflow/troubleshooting.md) - 常见问题解决方案
- [命令文档](../user/commands/) - 详细的命令说明
- [配置文档](../user/configuration/) - 配置文件参数详解

## 9. 快速参考

以下是本指南中使用的关键命令速查表。

### 常用命令速查

```bash
# 初始化项目
mise run init:experiment projects/my-project

# 进入项目目录
cd projects/my-project

# 完整流水线
just run-all

# 单个步骤
just recommend-parse-sensors
just parse-sensors
just process-clean
just report-timeseries

# 查看所有命令
just --list
```

### 目录结构速览

```
projects/my-project/
├── Justfile          # 项目命令
├── pre-masts/        # 原始数据
├── masts/            # 标准化数据
├── mesos/            # 中尺度数据
├── raw/              # 解析输出
├── clean/            # 清理输出
├── rep-ts/           # 报告输出
└── *.toml            # 各步骤配置文件
```

---

恭喜您完成 CleanMast 快速入门！如需更多帮助，请参阅详细文档或联系技术支持。
