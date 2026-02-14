# 中尺度数据重构

## 算法

Mesoscale Reconstruction（中尺度重构）

## 概述

中尺度数据重构算法利用训练好的统计模型，将中尺度再分析数据（如ERA5、MERRA-2等）转换为与测风塔观测相匹配的数值，填补测风塔数据中的长期缺失。该方法基于前期训练阶段建立的转换关系，将大尺度气象模型数据降尺度到具体测风塔位置，实现长时间序列的数据重构。

## 核心原理

中尺度重构建立在「训练-应用」两阶段范式之上。训练阶段利用测风塔完整观测期数据与同期中尺度数据，建立两者之间的统计转换关系。这种关系能够捕捉大尺度气象场与局地测风塔之间的系统性偏差，包括地形效应、高度差异、局地环流特征等。

重构阶段则将这一转换关系应用于任意时间点的中尺度数据，生成与测风塔等效的观测值。当测风塔传感器出现故障或数据质量不达标时，系统自动调用中尺度重构数据进行填补，确保时间序列的完整性。

## 实现细节

### 源代码位置

- **核心逻辑**: `CleanMastProject/src/ReconstructMeso/Core.jl`
- **配置定义**: `CleanMastProject/src/Types/ReconstructMesoConfig.jl`
- **模型抽象**: `CleanMastProject/src/Types/MastReferenceModel.jl`
- **具体实现**: `CleanMastProject/src/WindSpeedModels/SectorizedRegression*.jl`

### 数据准备与时间对齐

**函数**: `prepare_merge_data(mast_ts, meso_ts, reconstruction_time_range)` (`Core.jl:31-43`)

**处理逻辑**:

该函数负责将测风塔时间序列与中尺度数据进行时间对齐，确保后续处理的数据一致性。实现位于 `CleanMastProject/src/ReconstructMeso/Core.jl`。

1. **检测代表性时间间隔**: 从测风塔数据中识别原始采样间隔（如10分钟）
2. **规则化测风塔数据**: 将测风塔数据重采样到指定的规则时间间隔
3. **插值对齐中尺度数据**: 将中尺度数据的时间戳与测风塔完全对齐，生成与测风塔等长的时间序列

**关键要求**: 时间戳必须完全一致，否则后续的合并操作将失败。

### 模型加载与重建应用

**函数**: `merge_reconstruct_meso(mast_payload, meso, model, reconstruction_time_range)` (`Core.jl:49-60`)

处理步骤:
1. **准备合并数据**: 调用 `prepare_merge_data` 对齐时间序列
2. **应用重建模型**: 调用 `reconstruct(model, prepared_meso)` 生成重建后的测风塔等效值
3. **创建载荷对象**: `ReconstructionPayload(prepared_mast, mast_payload.reconstruction_sources)`
4. **合并数据并追踪来源**: 调用 `merge_reconstruct!(mast_payload, reconstructed_meso, "meso", getModelName(model))`

**处理逻辑**:

该函数是中尺度重构的核心入口，负责协调数据准备、模型应用和数据合并的全过程。实现位于 `CleanMastProject/src/ReconstructMeso/Core.jl`。

1. **准备合并数据**: 调用 `prepare_merge_data` 函数对齐测风塔与中尺度数据的时间序列
2. **应用重建模型**: 将对齐后的中尺度数据输入训练好的统计模型，生成重构后的测风塔等效值
3. **创建载荷对象**: 封装处理后的测风塔数据和重建来源信息
4. **合并数据并追踪来源**: 调用 `merge_reconstruct!` 函数将重构数据合并到测风塔数据，并记录每个重构值的数据来源

### 数据合并策略

**函数**: `merge_reconstruct!(mast_payload, reconstructed, source_id, model_id)` (`MastReferenceModel.jl:160-193`)

**核心合并逻辑**:
1. **时间戳验证**: 确保重建数据与测风塔数据长度相同且时间戳完全一致，否则抛出 `ArgumentError`
2. **查找公共传感器**: 筛选测风塔与重建数据中共同的传感器列
3. **填充缺失值**: 仅对测风塔数据中 `ismissing` 的行进行填充，保留原始有效值
4. **向量化操作**: 使用 `df[missing_mask, col] .= reconstructed.df[missing_mask, col]` 进行高效批量赋值
5. **来源追踪**: 为每个填充的值创建 `ReconstructionSource` 记录

**实现逻辑**:

该函数负责将重构数据合并到测风塔载荷中，并记录数据来源。实现位于 `CleanMastProject/src/Types/MastReferenceModel.jl`。

1. **时间戳验证**: 验证重建数据与测风塔数据长度相同且时间戳完全一致，若不匹配则抛出 `ArgumentError`
2. **查找公共传感器**: 筛选测风塔与重建数据中共同的传感器列
3. **向量化缺失值填充**: 构造缺失值掩码，对测风塔数据中 `ismissing` 的行进行向量化批量赋值
4. **来源追踪记录**: 为每个填充的重构值创建 `ReconstructionSource` 记录，包含时间戳、传感器列名、数据来源和模型标识

### 具体模型示例：分扇区回归模型

**训练阶段** (`SectorizedRegressionTraining.jl:25-71`):
- 按风向扇区划分数据（如0-30°, 30-60°等）
- 对每个扇区独立拟合线性回归: `mast_speed = slope * meso_speed + intercept`
- 若某扇区样本不足 (< 5条)，使用全局回归参数作为后备

**重建阶段** (`SectorizedRegressionReconstruction.jl:21-51`):
- 对每个时间点，根据中尺度风向确定所属扇区
- 应用对应扇区的回归公式计算重建值
- 结果限制在 [0.5, 25.0] m/s 物理范围内

**重建算法逻辑**:

该分扇区回归重建算法位于 `CleanMastProject/src/WindSpeedModels/SectorizedRegressionReconstruction.jl`。

1. **输入处理**: 同时接收中尺度风速和风向数据
2. **缺失值检查**: 若任一输入值为 `missing`，直接返回 `missing`
3. **扇区模型选择**: 根据风向调用 `get_sector_model()` 获取对应扇区的回归模型
4. **回归计算**: 应用扇区特定的线性回归公式：`重构值 = slope × 中尺度风速 + intercept`
5. **物理范围约束**: 使用 `clamp()` 函数将结果限制在 [0.5, 25.0] m/s 范围内，确保物理合理性

### 来源追踪机制

**数据结构**: `ReconstructionSource` (`MastReferenceModel.jl:103-108`)

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | DateTime | 重建值的时间戳 |
| `sensor_column` | Symbol | 重建的传感器列名 |
| `reference_name` | String | 数据来源标识（如 `"meso"`） |
| `model_id` | String | 使用的模型标识（如 `"8-sector"`） |

**输出格式**: 可通过 `show_as_dataframe(sources)` 转换为 DataFrame 用于分析报告

## 配置示例

```toml
# reconstruct-meso.toml

# 测风塔配置
[[masts]]
name = "PN01"

# 输入数据源
[masts.input]
type = "csv"
path = "projects/pn-masts/outputs/cleaned/PN01_cleaned_10min.parquet"

# 输出数据源
[masts.output]
type = "parquet"
path = "projects/pn-masts/outputs/reconstructed_meso/PN01_reconstructed_meso.parquet"

# 重构时间范围
[masts.time_range]
start = "2020-01-01T00:00:00"
end = "2023-12-31T23:50:00"

# 模型配置 - 风速
[masts.models.windspeed]
method = "SectorizedRegression"      # 分扇区回归方法
meso_name = "ERA5"                   # 中尺度数据源名称
model_file = "models/PN01_windspeed_era5_model.jls"

# 模型配置 - 风向
[masts.models.winddirection]
method = "DirectionOffset"           # 方向偏移方法
meso_name = "ERA5"
model_file = "models/PN01_winddirection_era5_model.jls"

# 中尺度数据源
[[mesos]]
name = "ERA5"
type = "csv"
path = "data/era5/era5_pn_region_2020_2023.csv"
```

## 默认推荐值

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `method` | `SectorizedRegression` | 分扇区回归，对复杂地形风向效应更鲁棒 |
| 扇区数量 | 8-12 | 根据风向玫瑰图特征分布调整 |
| 最小扇区样本数 | 5 | 低于此值使用全局回归参数 |
| 重建值下限 | 0.5 m/s | 避免零风速或负值 |
| 重建值上限 | 25.0 m/s | 过滤异常高值 |
| 时间对齐容差 | 精确匹配 | 使用 `interpolate_timeseries` 确保时间戳完全一致 |

## 适用场景

**数据缺口较大时**：当测风塔存在连续数周甚至数月的长期数据缺失，传统的插值方法已无法有效填补，此时中尺度重构是唯一可行的解决方案。

**长期代表性评估时**：风能项目需要进行20-30年的长期风能资源评估，而实际观测期通常仅有1-2年。通过中尺度重构，可以将短期观测「延长」至与再分析数据等长的历史时期。

**多年度对比分析时**：需要比较不同年份的风能特征时，可利用中尺度数据重构各年度的完整时间序列，支持年际变化分析。

**与历史工程数据衔接时**：当项目需要与多年前的历史测风数据进行对比分析，但原始数据已不可获取时，中尺度重构可以提供合理的历史参考值。

## 输入数据

**测风塔时间序列数据**：包含待填补缺失的原始测风塔观测数据，时间戳和关键变量（风速、风向等）需完整记录。数据应经过清理阶段处理，移除了明显异常值。

**训练好的中尺度转换模型**：由`train-meso`命令生成并保存的统计模型文件。模型封装了中尺度数据与测风塔数据之间的转换规则。

**中尺度再分析数据**：目标时间段的中尺度网格数据，包含风速、风向、温度、气压等气象变量。数据来源可为ERA5、MERRA-2、CFSR等公开再分析数据集。

**重构配置参数**：指定目标时间范围、重构变量、重构高度层等控制参数。

## 输出数据

**重构后的测风塔时间序列**：原始数据中的缺失时段被中尺度重构数据填补，其余时段保持原始观测不变。输出数据保留完整的时间序列结构。

**重构来源标记**：系统自动记录每个数据点的来源（原始观测或中尺度重构），便于后续质量评估和不确定性分析。

**重构质量报告**：包含重构结果的统计摘要，如重构数据覆盖率、与原始数据的统计特征对比等信息。

## 处理流程

**第一步：数据准备与时间对齐**

加载测风塔时间序列数据和中尺度数据，确保两者时间戳对齐到统一时区。将中尺度数据的时间分辨率调整为与测风塔一致（如从小时数据插值到10分钟数据）。

**第二步：应用转换模型**

将处理后的中尺度数据输入训练好的转换模型，生成重构后的测风塔等效值。模型基于训练阶段学习的转换规则，将网格尺度的中尺度数值转换为符合测风塔局地特征的估计值。

**第三步：数据合并**

将重构数据与原始测风塔数据合并，缺失时段使用重构值填充。系统追踪并记录每个数据点的来源信息。

**第四步：质量检验**

对重构结果进行基本的质量检验，包括统计特征对比（如均值、方差）、时间连续性检查等。识别并标记可能的重构异常值。

## 质量影响因素

**模型质量**：转换模型是重构效果的核心决定因素。训练数据越丰富、统计关系越稳定，重构结果越可靠。模型在训练期表现不佳时，重构结果的质量也会受到影响。

**中尺度数据准确性**：不同再分析数据集在特定地区和时段的表现存在差异。ERA5通常在陆地区域表现较好，MERRA-2在海洋区域有独特优势。选择适合项目区域的中尺度数据源很重要。

**缺失时段特征**：重构质量还取决于缺失时段的气象条件。极端天气事件（如台风、暴雪）期间，中尺度模型与实际观测的偏差可能增大，重构不确定性也相应提高。

**时间跨度匹配**：重构时段与训练期的重叠程度影响结果可靠性。若重构时段与训练期的气候特征差异较大（如季节偏差），可能需要额外的校准调整。

## 与训练阶段的衔接

`reconstruct-meso`是`train-meso`的后续步骤。训练阶段建立的转换模型需要在重构阶段被正确加载和应用。两者的配置参数（如目标变量、高度层、统计类型）必须保持一致，否则会导致重构失败或结果错误。

典型的工作流程是：首先运行`train-meso`生成模型，然后配置`reconstruct-meso`并执行重构。重构可以针对训练期内的数据进行验证，也可以扩展到训练期外的任意历史时段。