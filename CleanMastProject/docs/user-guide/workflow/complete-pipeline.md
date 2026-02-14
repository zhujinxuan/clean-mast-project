# CleanMast 完整数据处理流水线

## 概述

本文档描述从原始测风塔数据到最终风资源评估报告的完整处理流程。CleanMast 采用模块化流水线设计，将复杂的数据处理任务分解为多个可独立执行的阶段，每个阶段都有明确的输入输出规范和验证检查点。

整个流水线包含 18 个处理步骤，涵盖数据解析、质量控制、塔影校正、数据重构、代表年校准以及报告生成等核心功能。用户可以根据实际需求选择执行全部步骤或仅执行特定阶段的步骤，这种灵活性使得 CleanMast 能够适应不同的项目规模和精度要求。

流水线的基本理念是"验证驱动"——每个阶段完成后都应进行质量检查，确保问题能够被及时发现和定位。这种设计大大降低了大规模数据处理的风险，提高了整体工作效率。建议在实际项目中按照文档顺序逐步执行每个阶段，并在每个检查点验证输出数据的质量。

## 流水线架构

### 整体流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CleanMast 完整流水线                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │  数据准备   │───▶│  数据清理   │───▶│ 塔影校正   │───▶│ 单塔重构   │ │
│  │ parse-sensor│    │   clean     │    │tower-shading│    │reconstruct- │ │
│  │             │    │             │    │             │    │   single    │ │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘ │
│        ↓                  ↓                  ↓                  ↓        │
│     raw/               clean/            tower-shading/      reconstruct- │
│                                                    single/              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ 交叉塔训练  │───▶│ 交叉塔重构  │───▶│ 中尺度训练  │───▶│ 中尺度重构  │ │
│  │ train-cross │    │reconstruct- │    │  train-meso │    │reconstruct- │ │
│  │             │    │    cross    │    │             │    │    meso     │ │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘ │
│        ↓                  ↓                  ↓                  ↓        │
│ train-reconstruct-  reconstruct-cross/    meso-models/      reconstruct- │
│      cross/                                                  meso/        │
│  ┌─────────────┐    ┌─────────────┐                                         │
│  │ 代表年校准  │───▶│ 报告生成   │                                         │
│  │representative│    │  report    │                                         │
│  │    -year    │    │    all     │                                         │
│  └─────────────┘    └─────────────┘                                         │
│        ↓                  ↓                                                │
│ representative-      report-masts/                                          │
│     year/                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 处理阶段概览

流水线按功能可划分为六个主要阶段，每个阶段承担特定的数据处理任务。第一阶段负责数据准备，将各种格式的原始数据解析为统一的结构化格式；第二阶段进行数据质量控制，应用规则检测和标记异常数据；第三阶段处理塔影效应，校正测风塔结构对测量的影响；第四阶段利用传感器相关性填补数据缺口；第五阶段结合中尺度数据扩展时间序列覆盖范围；第六阶段进行长期校准并生成最终报告。

每个阶段都遵循"推荐配置 → 执行处理 → 验证输出"的三步模式。使用 `recommend` 命令可以快速生成适合项目特点的配置文件，执行完处理步骤后应检查输出目录和统计文件确认处理效果。这种标准化的流程设计使得项目管理更加规范，也便于问题追溯和结果复现。

## 项目准备阶段

### 任务清单

- [ ] 创建项目目录结构
- [ ] 准备原始测风塔数据文件
- [ ] 准备中尺度再分析数据（如需要长期扩展）
- [ ] 确认传感器格式配置文件
- [ ] 生成数据解析配置

### 数据准备流程

在开始任何数据处理之前，需要完成项目目录的创建和原始数据的准备工作。首先使用 Python CLI 初始化项目结构，这会自动生成标准化的目录模板和数据组织规范。测风塔原始数据应放置在 `pre-masts/` 目录下进行预处理，中尺度数据则直接放入 `mesos/` 目录。

原始数据预处理是关键的前置步骤，使用 Claude Code 的 `preprocess-mast-data` skill 可以自动完成数据格式验证、编码转换、列名标准化等任务。预处理完成后，输出文件会自动保存到 `masts/` 目录，形成标准化的输入数据格式。这一步骤确保了后续处理流程能够使用格式一致、质量可控的输入数据。

### 配置生成命令

```bash
# 初始化项目（使用 Python CLI）
uv run cleanmast init projects/my-windfarm

# 生成传感器解析配置
julia bin/CleanMast.jl recommend parse-sensors projects/my-windfarm
```

### 输出目录结构

项目初始化后将创建以下目录结构：

```
projects/my-windfarm/
├── pre-masts/              # 原始测风塔数据（预处理前）
│   └── M01/
├── masts/                  # 预处理后的测风塔数据
├── mesos/                  # 中尺度再分析数据
└── parse-sensors.toml      # 传感器解析配置
```

### 验证检查点

执行数据解析前，应确认以下条件已满足：原始数据文件全部存在且可读、传感器格式文件与数据列结构匹配、输出目录具有写入权限。解析完成后检查 `raw/` 目录中的 CSV 文件和传感器配置 TOML 文件，确认时间戳连续性和数据完整性。

## 阶段一：数据解析

### 任务清单

- [ ] 执行 `project parse-sensors` 解析原始数据
- [ ] 验证生成的原始数据文件
- [ ] 检查传感器元数据配置
- [ ] 确认数据时间范围和采样间隔

### 输入与输出

**输入文件**：原始测风塔数据文件（支持 NRG、FREELDM 等格式）、传感器格式定义文件、parse-sensors.toml 配置文件。

**输出文件**：`raw/<数据源名称>.csv` 标准化时间序列数据、`raw/<数据源名称>.sensors.toml` 传感器元数据配置。

### 执行命令

```bash
# 执行传感器数据解析
julia bin/CleanMast.jl project parse-sensors projects/my-windfarm/parse-sensors.toml
```

### 配置说明

传感器解析配置定义了原始数据列与标准化传感器类型之间的映射关系。每个测风塔数据源需要指定输入文件路径、输出名称以及使用的传感器格式模板。配置中还可以定义列的缺失值处理规则和数据类型转换选项。

详细的配置参数说明见 [parse-sensors 配置指南](../../configuration/config-files/parse-sensors.md)。

### 验证检查点

解析完成后，执行以下验证步骤：检查输出 CSV 文件的列名是否符合预期、验证时间戳格式和连续性、确认传感器元数据中的高度和类型信息正确、抽样检查数值范围是否在合理区间。如发现问题，应检查原始数据文件和传感器格式配置是否匹配。

### 常见问题

如果解析过程中出现错误，常见原因包括：原始数据编码不被支持、传感器格式模板与实际列结构不匹配、缺失值标记方式与配置不符。解决方法是检查原始数据文件的实际格式，调整传感器格式配置文件，或在配置中明确指定缺失值的处理方式。

## 阶段二：数据清理

### 任务清单

- [ ] 使用 `recommend process-clean` 生成清理配置
- [ ] 执行 `process clean` 应用清理规则
- [ ] 查看清理统计报告
- [ ] 分析标记的异常数据分布
- [ ] 调整清理参数（如需要）

### 输入与输出

**输入文件**：`raw/` 目录下的传感器配置 TOML 文件和时间序列 CSV 数据、`formats/clean/` 下的清理规则文件。

**输出文件**：`clean/<测风塔名称>.csv` 清理后的时间序列数据、`clean/<测风塔名称>.sensors.yaml` 更新后的传感器配置、`process-stats/clean-<测风塔名称>.yaml` 清理统计信息。

### 执行命令

```bash
# 生成数据清理配置
julia bin/CleanMast.jl recommend process-clean projects/my-windfarm

# 执行数据清理
julia bin/CleanMast.jl process clean projects/my-windfarm/process-clean.toml
```

### 清理规则类型

数据清理包含三类核心规则：数值范围验证检查传感器测量值是否在物理合理区间内；层差检查验证同一时刻不同高度传感器测量值的逻辑一致性；结冰检测识别因结冰导致的异常低速数据。每类规则都可以独立启用或禁用，并可以配置具体的阈值参数。

详细的规则配置说明见 [process-clean 配置指南](../../configuration/config-files/process-clean.md)。

### 验证检查点

清理完成后，重点检查以下内容：查看统计报告中各类规则的触发次数和比例、分析被标记为异常的数据在时间上的分布模式、抽样核实被剔除的数据是否确实异常。对于清理结果有疑虑时，可以调整规则参数后重新执行，或人工复核部分数据点。

### 时间估计

单个测风塔的数据清理通常在数秒到数分钟内完成，具体取决于数据量大小和规则复杂度。对于包含多个测风塔的大型项目，建议批量处理全部数据后再统一分析清理效果。

## 阶段三：塔影校正

### 任务清单

- [ ] 使用 `recommend tower-shading` 生成塔影校正配置
- [ ] 执行 `process tower-shading` 进行塔影检测和校正
- [ ] 分析塔影影响范围和校正效果
- [ ] 验证校正后的数据合理性

### 输入与输出

**输入文件**：`clean/` 目录下的传感器配置 YAML 文件和时间序列 CSV 数据。

**输出文件**：`tower-shading/<测风塔名称>.csv` 塔影校正后的数据、`tower-shading/<测风塔名称>.sensors.yaml` 更新后的传感器配置、`process-stats/tower-shading-<测风塔名称>.yaml` 校正统计信息。

### 执行命令

```bash
# 生成塔影校正配置
julia bin/CleanMast.jl recommend tower-shading projects/my-windfarm

# 执行塔影校正
julia bin/CleanMast.jl process tower-shading projects/my-windfarm/tower-shading.toml
```

### 塔影校正原理

测风塔的金属结构会对迎风面和背风面的传感器产生气流干扰，导致测量值偏低或偏高。塔影校正通过分析不同方向上风速的差异模式，识别受塔影影响的数据，并使用相邻高度未受影响传感器的数据进行校正。校正效果取决于塔架几何结构和传感器布置方案。

详细的塔影校正算法说明见 [塔影校正算法文档](../../technical/algorithms/tower-shading.md)。

### 验证检查点

校正完成后，检查以下指标：风向玫瑰图是否更加对称、校正前后风速分布的变化情况、不同高度传感器之间相关性的改善程度。如果校正结果异常，应检查塔架参数配置是否正确，或考虑调整校正灵敏度参数。

### 时间估计

塔影校正的处理时间与数据量和塔架复杂度相关，通常为清理步骤的 1.5 到 2 倍。对于结构复杂的测风塔，可能需要人工调整配置参数后多次尝试。

## 阶段四：单塔数据重构

### 任务清单

- [ ] 使用 `recommend reconstruct-single` 生成重构配置
- [ ] 执行 `process reconstruct-single` 进行传感器相关性重构
- [ ] 分析重构填补的数据量
- [ ] 评估重构质量的统计指标

### 输入与输出

**输入文件**：`tower-shading/` 目录下的传感器配置和时间序列数据。

**输出文件**：`reconstruct-single/<测风塔名称>.csv` 重构后的数据、`reconstruct-single/<测风塔名称>.sensors.yaml` 更新后的传感器配置、`process-stats/reconstruct-single-<测风塔名称>.yaml` 重构统计信息。

### 执行命令

```bash
# 生成单塔重构配置
julia bin/CleanMast.jl recommend reconstruct-single projects/my-windfarm

# 执行单塔重构
julia bin/CleanMast.jl process reconstruct-single projects/my-windfarm/reconstruct-single.toml
```

### 重构方法说明

单塔重构利用同一测风塔内不同高度传感器之间的相关性来填补数据缺口。当某个传感器出现数据缺失时，系统会根据该时刻其他高度传感器的测量值，通过预先建立的相关性模型估算缺失值。相关性模型基于完整数据期间的历史数据训练，能够捕捉风速随高度变化的规律。

详细的配置参数说明见 [reconstruct-single 配置指南](../../configuration/config-files/reconstruct-single.md)。

### 验证检查点

重构完成后，核查以下内容：查看填补的数据量占总体数据量的比例、抽样对比重构值与原始值的差异、检验重构数据与相邻高度数据的连续性。重构比例过高可能表明原始数据质量问题严重，需要返回前面的清理阶段进行调整。

### 时间估计

单塔重构的处理时间取决于测风塔高度层数和相关性模型的复杂度，通常与塔影校正相当或略长。

## 阶段五：交叉塔训练与重构（可选）

### 任务清单

- [ ] 使用 `recommend train-cross` 生成交叉训练配置
- [ ] 执行 `process train-cross` 训练交叉测风塔相关性模型
- [ ] 使用 `recommend reconstruct-cross` 生成交叉重构配置
- [ ] 执行 `process reconstruct-cross` 进行跨塔数据填补
- [ ] 评估多塔数据的一致性

### 输入与输出

**输入文件**：`reconstruct-single/` 目录下多个测风塔的重构数据。

**输出文件**：`train-reconstruct-cross/` 训练结果目录、`reconstruct-cross/<测风塔名称>.csv` 交叉重构后的数据。

### 执行命令

```bash
# 生成交叉训练配置
julia bin/CleanMast.jl recommend train-cross projects/my-windfarm

# 执行交叉训练
julia bin/CleanMast.jl process train-cross projects/my-windfarm/train-cross.toml

# 生成交叉重构配置
julia bin/CleanMast.jl recommend reconstruct-cross projects/my-windfarm

# 执行交叉重构
julia bin/CleanMast.jl process reconstruct-cross projects/my-windfarm/reconstruct-cross.toml
```

### 适用场景

交叉塔重构适用于项目包含多个测风塔且相互距离较近的情况。通过分析测风塔之间的空间相关性，可以用数据完整的测风塔来填补另一测风塔的缺口。这种方法的有效性取决于测风塔之间的距离和地形条件，距离越近相关性通常越强。

### 时间估计

交叉塔训练和重构的计算量与测风塔数量和数据量成正比，处理时间通常为单塔重构的倍数。

## 阶段六：中尺度模型训练

### 任务清单

- [ ] 使用 `recommend train-meso` 生成中尺度训练配置
- [ ] 执行 `process train-meso` 训练测风塔-中尺度相关性模型
- [ ] 分析相关性模型的质量指标
- [ ] 选择合适的重构方法（16扇区或全方向）

### 输入与输出

**输入文件**：`reconstruct-single/` 或 `reconstruct-cross/` 目录下的测风塔数据、`mesos/` 目录下的中尺度数据。

**输出文件**：`meso-models/<测风塔>/<中尺度源>/windspeed|winddirection/<方法>.jld2` 训练好的模型文件、`meso-models/train-meso-results.toml` 训练结果汇总、`meso-models/<测风塔>/stats/<中尺度源>-training-stats.yaml` 训练统计信息。

### 执行命令

```bash
# 生成中尺度训练配置
julia bin/CleanMast.jl recommend train-meso projects/my-windfarm

# 执行中尺度模型训练
julia bin/CleanMast.jl process train-meso projects/my-windfarm/train-meso.toml
```

### 模型类型说明

中尺度训练支持三种模型类型：16扇区模型将 360 度分为 16 个 22.5 度扇区，每个扇区独立建立风速回归关系，能够捕捉风向对相关性的影响；全方向模型使用所有数据建立一个统一的回归关系，计算简单但可能忽略方向性差异；风向常数偏移模型专门用于校正风向的系统偏差。

详细的配置参数和模型选择建议见 [train-meso 配置指南](../../configuration/config-files/train-meso.md)。

### 验证检查点

训练完成后，重点检查 `train-meso-results.toml` 中的相关性指标：风速相关系数应高于 0.7 才适合用于重构、风向标准差偏移应小于 30 度、用于训练的数据覆盖期应足够长（建议不少于半年）。如果相关性不理想，可以尝试更换中尺度数据源或调整模型类型。

### 时间估计

中尺度模型训练的计算量较大，处理时间取决于测风塔数量、中尺度数据量以及选择模型类型的复杂度。通常需要数分钟到数十分钟。

## 阶段七：中尺度数据重构

### 任务清单

- [ ] 使用 `recommend reconstruct-meso` 生成中尺度重构配置
- [ ] 执行 `process reconstruct-meso` 进行长期数据扩展
- [ ] 分析重构后数据的时间覆盖范围
- [ ] 评估重构不确定度

### 输入与输出

**输入文件**：`reconstruct-single/` 或 `reconstruct-cross/` 目录下的测风塔数据、`mesos/` 目录下的中尺度数据、训练好的 `.jld2` 模型文件。

**输出文件**：`reconstruct-meso/<测风塔名称>.csv` 中尺度重构后的完整数据、`reconstruct-meso/<测风塔名称>.sensors.yaml` 更新后的传感器配置、`process-stats/reconstruct-meso-<测风塔名称>.yaml` 重构统计信息。

### 执行命令

```bash
# 生成中尺度重构配置
julia bin/CleanMast.jl recommend reconstruct-meso projects/my-windfarm

# 执行中尺度重构
julia bin/CleanMast.jl process reconstruct-meso projects/my-windfarm/reconstruct-meso.toml
```

### 时间范围配置

中尺度重构可以扩展到任意时间范围，通常根据项目需求设定。典型的代表年校准需要扩展到 10 年以上的历史数据。配置中的 `start_time` 和 `end_time` 参数定义了重构的时间边界，应确保中尺度数据能够覆盖这个完整区间。

详细的配置参数说明见 [reconstruct-meso 配置指南](../../configuration/config-files/reconstruct-meso.md)。

### 验证检查点

重构完成后，确认以下内容：数据时间范围是否符合预期、原始数据与重构数据的过渡是否自然、重构统计信息中的不确定度指标是否合理。不确定度过高可能表明中尺度模型质量不佳，需要返回训练阶段进行调整。

### 时间估计

中尺度重构的处理时间与目标时间跨度成正比，重构 10 年数据通常需要数分钟。

## 阶段八：代表年校准

### 任务清单

- [ ] 使用 `recommend representative-year` 生成代表年配置
- [ ] 执行 `process representative-year` 进行代表年校准
- [ ] 验证校准后的数据代表性
- [ ] 分析各扇区校准因子的合理性

### 输入与输出

**输入文件**：`reconstruct-meso/` 目录下的测风塔数据、`mesos/` 目录下的中尺度数据、16 扇区风速模型文件。

**输出文件**：`representative-year/<测风塔名称>.csv` 代表年校准后的数据、`representative-year/<测风塔名称>.sensors.yaml` 更新后的传感器配置、`process-stats/representative-year-<测风塔名称>.yaml` 校准统计信息。

### 执行命令

```bash
# 生成代表年校准配置
julia bin/CleanMast.jl recommend representative-year projects/my-windfarm

# 执行代表年校准
julia bin/CleanMast.jl process representative-year projects/my-windfarm/representative-year.toml
```

### 校准方法说明

代表年校准使用 16 扇区方法，基于中尺度数据识别目标年份相对于长期平均条件的偏差，并为每个风向扇区计算独立的校准因子。这种方法能够考虑不同风向下的地形和气象特征差异，提供更准确的长期风资源估计。

详细的算法说明见 [代表年校准算法文档](../../technical/algorithms/representative-year.md)。

### 验证检查点

校准完成后，检查以下内容：各扇区校准因子是否在合理范围内（通常 0.8 到 1.2）、校准后的年平均风速是否接近预期值、极端风速的分布是否合理。异常校准因子可能指示数据质量问题或中尺度模型失效。

### 时间估计

代表年校准的处理时间取决于数据量和扇区数量，通常为中尺度重构时间的 1.5 倍左右。

## 阶段九：风机时间序列导出（可选）

### 任务清单

- [ ] 使用 `recommend wt-timeseries` 生成导出配置
- [ ] 执行 `process wt-timeseries` 导出 MeteoDyn 格式数据
- [ ] 验证导出数据的格式正确性

### 输入与输出

**输入文件**：`representative-year/` 目录下的校准后数据。

**输出文件**：`wt-timeseries/<风机名称>.csv` MeteoDyn 格式的时间序列数据。

### 执行命令

```bash
# 生成风机时间序列导出配置
julia bin/CleanMast.jl recommend wt-timeseries projects/my-windfarm

# 导出 MeteoDyn 时间序列
julia bin/CleanMast.jl process wt-timeseries projects/my-windfarm/wt-timeseries.toml
```

### 适用场景

此步骤用于将处理后的风数据导出为第三方风资源评估软件（如 MeteoDyn WT）所需的格式。如果项目不需要此类集成，可以跳过此步骤。

## 阶段十：报告生成

### 任务清单

- [ ] 使用 `recommend report-all` 生成分析配置
- [ ] 执行 `report all` 生成综合分析报告
- [ ] 查看风资源评估结果
- [ ] 分析数据质量报告
- [ ] 导出 PDF 或 HTML 格式报告

### 执行命令

```bash
# 生成所有分析配置文件
julia bin/CleanMast.jl recommend report-all projects/my-windfarm

# 执行综合分析报告
julia bin/CleanMast.jl report all projects/my-windfarm
```

### 报告内容

综合报告包含以下主要部分：风速分布分析和威布尔参数拟合、风向玫瑰图和风向频率统计、湍流强度评估、垂直风切变分析、极值风速估算、数据完整性统计、重构质量评估以及 IEC/EN 标准风机级别判定。

详细的报告内容说明见 [report all 命令文档](../../commands/report-all.md)。

### 输出目录结构

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

### 查看报告

使用 Typst 编译器生成 PDF 格式报告：

```bash
cd projects/my-windfarm/report-masts
typst compile data-quality-report.typ data-quality-report.pdf
```

### 时间估计

报告生成时间取决于数据量和分析内容的丰富程度，通常需要数分钟到数十分钟。复杂项目的综合报告可能需要更长时间。

## 完整流水线执行

### 一键执行全部步骤

对于完整项目，可以使用 `process steps --all` 命令按顺序执行所有 18 个处理步骤：

```bash
julia bin/CleanMast.jl process steps --all projects/my-windfarm
```

此命令会自动依次执行推荐配置生成和数据处理步骤，每个步骤完成后会显示执行状态。遇到错误时会停止并提示恢复命令。

### 分步执行模式

在开发和调试阶段，建议使用步骤范围控制功能分批执行：

```bash
# 仅执行数据准备步骤 (1-6)
julia bin/CleanMast.jl process steps --from 1 --to 6 projects/my-windfarm

# 仅执行模型训练步骤 (7-12)
julia bin/CleanMast.jl process steps --from 7 --to 12 projects/my-windfarm

# 从特定步骤继续执行
julia bin/CleanMast.jl process steps --from 12 projects/my-windfarm
```

### 查看可用步骤列表

```bash
julia bin/CleanMast.jl process steps --list
```

此命令显示所有 18 个步骤的名称和描述，便于了解整体流程和选择执行范围。

## 典型时间估计

### 数据处理阶段

| 阶段 | 典型时间 | 影响因素 |
|------|---------|----------|
| 数据解析 | 10-60 秒/文件 | 文件大小、格式复杂度 |
| 数据清理 | 1-5 分钟/塔 | 数据量、规则复杂度 |
| 塔影校正 | 2-10 分钟/塔 | 塔架复杂度、数据量 |
| 单塔重构 | 2-10 分钟/塔 | 高度层数、相关性模型 |
| 中尺度训练 | 5-30 分钟/项目 | 测风塔数量、数据量 |
| 中尺度重构 | 1-10 分钟/塔 | 时间跨度、模型类型 |
| 代表年校准 | 2-15 分钟/塔 | 数据量、扇区数量 |
| 报告生成 | 5-30 分钟/项目 | 分析内容丰富程度 |

### 总体评估

对于包含 2-3 个测风塔、数据期 1-3 年的典型项目，完整流水线的执行时间约需 30-60 分钟。如果项目规模更大或需要进行跨塔分析，处理时间会相应增加。建议在首次运行时预留充足时间，并根据实际需求优化配置参数。

## 验证与质量控制

### 各阶段检查清单

每个处理阶段完成后，应执行以下验证操作：

第一阶段数据解析后，抽样检查时间戳连续性、列名规范性以及数值范围合理性。第二阶段数据清理后，查看各类规则的触发统计，分析异常数据的时空分布模式。第三阶段塔影校正后，检查风向玫瑰图对称性和不同高度数据的相关性变化。第四阶段单塔重构后，评估填补数据比例和重构值的统计特征。第五至第七阶段涉及中尺度处理时，重点检查相关性模型质量指标和重构不确定度。第八阶段代表年校准后，验证各扇区校准因子的合理性。最终的报告生成阶段应全面审核风资源评估结论的可信度。

### 错误处理与恢复

如果处理过程中出现错误，系统会显示详细的错误信息和恢复建议。常见的错误原因包括：配置文件路径错误、输入文件缺失、权限不足或数据格式问题。根据错误提示修正问题后，可以使用 `process steps --from <步骤号>` 命令从失败步骤继续执行，而无需重新运行整个流水线。

## 相关文档

### 命令文档

- [project 命令](../../commands/project.md) - 项目设置和解析命令
- [process steps 命令](../../commands/process/process-steps.md) - 流水线控制命令
- [process clean 命令](../../commands/process/clean.md) - 数据清理命令
- [process tower-shading 命令](../../commands/process/tower-shading.md) - 塔影校正命令
- [process reconstruct-single 命令](../../commands/process/reconstruct-single.md) - 单塔重构命令
- [process train-meso 命令](../../commands/process/train-meso.md) - 中尺度训练命令
- [process reconstruct-meso 命令](../../commands/process/reconstruct-meso.md) - 中尺度重构命令
- [process representative-year 命令](../../commands/process/representative-year.md) - 代表年校准命令
- [report all 命令](../../commands/report-all.md) - 报告生成命令

### 配置文档

- [parse-sensors 配置](../../configuration/config-files/parse-sensors.md)
- [process-clean 配置](../../configuration/config-files/process-clean.md)
- [tower-shading 配置](../../configuration/config-files/tower-shading.md)
- [reconstruct-single 配置](../../configuration/config-files/reconstruct-single.md)
- [train-meso 配置](../../configuration/config-files/train-meso.md)
- [reconstruct-meso 配置](../../configuration/config-files/reconstruct-meso.md)

### 算法文档

- [数据清理算法](../../technical/algorithms/data-cleaning.md)
- [塔影校正算法](../../technical/algorithms/tower-shading.md)
- [单塔重构算法](../../technical/algorithms/reconstruct-single.md)
- [中尺度重构算法](../../technical/algorithms/reconstruct-meso.md)
- [代表年校准算法](../../technical/algorithms/representative-year.md)
