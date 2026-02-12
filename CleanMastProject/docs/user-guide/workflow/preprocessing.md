# CleanMast 数据预处理工作流

## 概述

本文档描述使用 Python preprocess-tools 包进行测风塔原始数据预处理的完整工作流。预处理是 CleanMast 数据处理流水线的第一个阶段，负责将各种格式的原始测风塔数据转换为标准化的输入格式，为后续的解析、清理和重构步骤做好准备。

预处理工具包包含四个核心命令：CSV 合并工具用于将多个数据文件合并为一个统一的时间序列；列名标准化工具将原始列名转换为 NRG 或 Lidar 标准格式；类型标准化工具将字符串类型的数值列转换为浮点数；时间戳标准化工具确保所有数据文件使用统一的时间戳格式。这些工具可以独立使用，也可以按顺序组合使用以完成完整的预处理流程。

## 安装与配置

### 环境准备

预处理工具作为 CleanMast Python 工作空间的一部分提供。首次使用前需要安装项目依赖：

```bash
# 从项目根目录执行
uv sync
```

此命令会自动创建 Python 虚拟环境并安装所有依赖包。安装完成后，后续使用均通过 `uv run preprocess` 命令调用预处理工具。

### 验证安装

执行以下命令验证预处理工具是否正确安装：

```bash
# 查看预处理工具的帮助信息
uv run preprocess --help
```

成功安装后应显示预处理工具的使用说明和可用子命令列表。如果出现错误，请检查 Python 版本和依赖包是否正确安装。

## 核心命令

### CSV 合并工具

CSV 合并工具用于将多个独立的测风塔数据文件合并为一个连续的时间序列文件。该工具能够自动处理不同文件之间的时间戳格式差异，并将数据按照时间顺序排列。合并过程中会检测重复记录，用户可以在配置中指定重复数据的处理策略。

```bash
# 合并 CSV 文件
uv run preprocess csv-merge path/to/merge-config.toml
```

合并工具支持配置重复检测阈值，当两个时间戳相差小于指定秒数时视为重复记录。详细的配置参数说明见 [CSV Merger 参考文档](packages/preprocess-tools/docs/csv-merger.md)。

### 列名标准化工具

列名标准化工具将原始数据文件中的列名转换为 CleanMast 期望的标准格式。该工具支持 NRG 和 Lidar 两种标准格式，能够识别多种常见的列名变体并将其映射到统一的命名规范。标准化后的列名便于后续处理步骤进行统一的列引用。

```bash
# 执行列名标准化
uv run preprocess col-normalizer path/to/col-name-config.toml
```

配置文件中需要指定源列名与目标列名的映射关系。工具会自动处理大小写差异和常见的前缀后缀变体。详细的映射规则说明见 [NRG 格式指南](packages/preprocess-tools/docs/nrg-format.md) 和 [Lidar 格式指南](packages/preprocess-tools/docs/lidar-format.md)。

### 类型标准化工具

类型标准化工具将数据文件中的字符串类型数值列转换为浮点数类型。许多原始测风塔数据使用字符串格式存储数值，可能包含缺失值标记、非数字字符串或其他格式变体。该工具能够识别这些变体并进行适当的转换，未知格式的值将保留为原始字符串。

```bash
# 执行类型标准化
uv run preprocess type-normalizer path/to/type-config.toml
```

类型转换过程中会跳过无法转换的值并记录警告信息。用户可以在配置中指定需要转换的列和期望的数据类型。详细的配置说明见 [命令参考文档](packages/preprocess-tools/docs/commands.md)。

### 时间戳标准化工具

时间戳标准化工具确保所有数据文件使用统一的时间戳格式。不同测风塔设备可能使用不同的时间戳格式和时区设置，该工具能够解析多种常见格式并将时间戳统一转换为标准格式。

```bash
# 执行时间戳标准化
uv run preprocess timestamp path/to/timestamp-config.toml
```

支持的输入格式包括 ISO 8601、常见的时间字符串格式以及各种本地化的时间表示。输出格式可在配置中指定，支持时区转换和时间区间验证。

## 典型工作流

### 完整预处理流程

对于包含多个数据文件的测风塔项目，建议按照以下顺序执行预处理步骤：

第一步是时间戳标准化，确保所有文件使用统一的格式：

```bash
uv run preprocess timestamp path/to/timestamp-config.toml
```

第二步执行列名标准化，将原始列名转换为标准格式：

```bash
uv run preprocess col-normalizer path/to/col-name-config.toml
```

第三步执行类型标准化，将字符串列转换为数值类型：

```bash
uv run preprocess type-normalizer path/to/type-config.toml
```

最后执行 CSV 合并，将处理后的文件合并为统一的输入数据：

```bash
uv run preprocess csv-merge path/to/merge-config.toml
```

### 部分预处理流程

如果原始数据已经部分标准化，可以跳过相应步骤。常见的变体包括：

**仅合并文件**：当所有文件已经具有标准格式时，可以直接执行合并：

```bash
uv run preprocess csv-merge path/to/merge-config.toml
```

**合并前处理**：当需要对合并后的数据进行标准化时，可以先合并再处理：

```bash
uv run preprocess csv-merge path/to/merge-config.toml
uv run preprocess col-normalizer path/to/col-name-config.toml
uv run preprocess type-normalizer path/to/type-config.toml
```

## 配置示例

### CSV 合并配置

```toml
# merge-config.toml
input_files = [
    "data/M01_2024_01.csv",
    "data/M01_2024_02.csv",
    "data/M01_2024_03.csv"
]
output_file = "processed/M01_2024_combined.csv"
duplicate_threshold_seconds = 60
```

### 列名标准化配置

```toml
# col-name-config.toml
input_file = "processed/M01_2024_combined.csv"
output_file = "processed/M01_2024_normalized.csv"
format = "nrg"
column_mappings = {}
```

### 类型标准化配置

```toml
# type-config.toml
input_file = "processed/M01_2024_normalized.csv"
output_file = "processed/M01_2024_typed.csv"
float_columns = [
    "wind_speed_80m",
    "wind_speed_60m",
    "wind_speed_40m",
    "wind_direction_80m",
    "temperature"
]
```

### 时间戳标准化配置

```toml
# timestamp-config.toml
input_file = "raw/M01_2024_01.csv"
output_file = "processed/M01_2024_01.csv"
input_format = "yyyy-mm-dd HH:MM:SS"
output_format = "ISO8601"
timezone = "UTC"
```

## 输入输出规范

### 输入文件要求

预处理工具支持 CSV 和 DAT 格式的测风塔数据文件。输入文件应满足以下要求：文件采用 UTF-8 或 GBK 编码；包含时间戳列且时间格式可识别；数值列中的缺失值使用统一的标记符（如 NA、NaN、空字符串等）。

对于不符合要求的文件，工具会显示错误信息并停止处理。用户需要先对文件进行格式调整，或在配置中指定容错参数。

### 输出文件格式

预处理工具的输出文件遵循 CleanMast 标准数据格式。合并后的文件包含统一的时间戳列和标准化后的数据列。时间戳使用 ISO 8601 格式，数值列使用双精度浮点数类型。输出文件可以直接用于 CleanMast 的后续处理步骤。

## 后续步骤

完成数据预处理后，可以继续执行 CleanMast 的完整数据处理流水线。预处理后的数据文件应放置在项目目录的 `masts/` 子目录下，然后使用 Julia 版本的 CleanMast 进行后续处理：

```bash
# 初始化项目结构
uv run cleanmast init projects/my-windfarm

# 放置预处理后的数据到 masts/ 目录
# 然后执行数据解析
julia bin/CleanMast.jl project parse-sensors projects/my-windfarm/parse-sensors.toml
```

## 相关文档

### 预处理工具文档

- [CSV Merger 参考](packages/preprocess-tools/docs/csv-merger.md) - CSV 文件合并详细说明
- [命令参考](packages/preprocess-tools/docs/commands.md) - 命令行参数完整说明
- [NRG 格式指南](packages/preprocess-tools/docs/nrg-format.md) - NRG 列头格式规范
- [Lidar 格式指南](packages/preprocess-tools/docs/lidar-format.md) - Lidar 数据格式规范

### CleanMast 主流程文档

- [完整数据处理流水线](complete-pipeline.md) - CleanMast 完整流水线说明
- [用户指南首页](../README.md) - CleanMast 使用指南入口
- [快速开始指南](../quickstart.md) - 快速上手教程

## 常见问题

### 问：预处理工具支持哪些文件编码？

预处理工具默认支持 UTF-8 和 GBK 编码。对于其他编码格式的文件，需要先使用外部工具转换为支持的编码，或在配置文件中指定编码参数。

### 问：如何处理缺失值？

预处理工具不会自动填充缺失值，而是将其保留为缺失状态。缺失值处理在后续的数据清理阶段进行，用户可以在清理配置中指定缺失值的处理规则。

### 问：合并时出现重复数据怎么办？

CSV 合并工具会在检测到重复数据时发出警告并跳过重复记录。用户可以在配置中调整 `duplicate_threshold_seconds` 参数来改变重复判定的时间阈值，或选择使用其他策略处理重复数据。
