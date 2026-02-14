# CleanMast 公共接口文档

本文档描述 CleanMast 工具包的公共 API，包括核心类型系统、配置类型、数据结构和关键工具函数。

## 1. 类型系统概述

CleanMast 使用 Julia 的模块化类型系统来组织数据结构和配置。所有公共类型按功能分为以下模块：

- **传感器类型模块 (SensorColumns)**：传感器元数据定义
- **时间序列模块 (MastTimeSeries)**：时序数据容器和加载/保存
- **配置类型模块 (ParseSensorsConfig, ProcessCleanConfig 等)**：各处理步骤配置
- **清洗规则模块 (CleanRules)**：数据质量规则定义
- **结果类型模块 (ViolationData, RepresentativeYear 等)**：分析结果数据结构

## 2. 核心数据类型

### 2.1 传感器列类型 (SensorColumns)

#### `ParsedSensor`

解析后的传感器定义，包含原始列名追踪功能。

**字段：**
- `columnName::Symbol`：标准化后的列名（Symbol 类型）
- `originalColumnNames::Vector{Symbol}`：原始列名列表（支持文件合并场景）
- `columnFormat::String`：创建该列使用的格式标识
- `sensorType::String`：传感器类型（"WindSpeed"、"WindDirection"、"Temperature"、"Pressure" 等）
- `sensorDirection::String`：传感器方向（"N/A" 表示全向传感器）
- `height::Float64`：传感器安装高度（米）
- `statType::String`：统计类型（"avg" 表示平均值）
- `unit::String`：数据单位
- `multiplier::Union{Float64, Nothing}`：可选的乘数因子

#### `SensorColumn`

标准化的传感器列定义，用于处理流程中的传感器元数据。

**字段：**
- `columnName::Symbol`：列名（Symbol 类型）
- `sensorType::String`：传感器类型
- `sensorDirection::String`：传感器方向
- `height::Float64`：高度
- `statType::String`：统计类型
- `unit::String`：单位

**工具函数：**
- `find_nearest_height_sensor(target_height, sensors, sensor_type, stat_type)`：查找指定类型和高度最接近的传感器
- `create_sensor_short_name(sensor)`：创建标准化的传感器短名称（如 "WS:80m"）
- `get_sensor_style_short_name(sensor_type)`：获取传感器类型的标准简称
- `make_typst_compatible_name(name)`：将传感器名称转换为 Typst 兼容格式

### 2.2 时间序列数据 (MastTimeSeries)

#### `TimeSeriesData`

时序数据的主容器类型。

**字段：**
- `df::DataFrame`：数据 DataFrame，包含时间戳和传感器数据列
- `sensors::Vector{SensorColumn}`：传感器元数据列表

#### `TimeSeriesSource`

时序数据的文件来源定义。

**字段：**
- `data::String`：数据文件路径
- `sensors::Union{String, Nothing}`：传感器描述文件路径

#### `TimeRange`

时间范围定义。

**字段：**
- `min::DateTime`：开始时间
- `max::DateTime`：结束时间

**文件加载/保存函数：**
- `load_timeseries(source, base_dir)`：加载时序数据，支持 CSV 和 Parquet 格式
- `save_timeseries(source, base_dir, data)`：保存时序数据
- `slice_timeseries_by_range(ts, time_range)`：按时间范围裁剪数据
- `detect_file_format(path)`：检测文件格式（:csv、:parquet、:unknown）
- `resolve_absolute_path(source, base_dir)`：解析绝对路径
- `adjust_relative_path(path, prefix)`：调整相对路径
- `adjust_timeseries_source_paths(source, prefix)`：调整 TimeSeriesSource 中的路径
- `adjust_timeseries_source_paths_to_parquet(source, prefix)`：调整路径并将 CSV 转换为 Parquet
- `convert_csv_to_parquet_path(path)`：将 CSV 路径转换为 Parquet 路径
- `extract_sensors_from_parquet(ds)`：从 Parquet 文件提取传感器元数据
- `sensors_to_column_metadata(sensors)`：将传感器定义转换为 Parquet 列元数据

### 2.3 清洗规则类型 (CleanRules)

#### `Rule`

数据清洗规则定义。

**字段：**
- `name::String`：规则名称
- `sensorType::String`：适用的传感器类型
- `height::HeightFilter`：高度过滤条件
- `criteria`：具体判断标准（可为 RangeCriteria、LayerDifferenceCriteria、IcingCriteria、AvailabilityCriteria、ManualCriteria）

#### 规则条件类型

- `RangeCriteria`：范围判断条件，包含 `min` 和 `max` 字段
- `LayerDifferenceCriteria`：层间差值条件，包含 `lower_layer_height`、`abs_diff`、`lower_wind_speed`
- `IcingCriteria`：结冰检测条件，包含 `time_range` 和 `max_change`
- `AvailabilityCriteria`：可用性条件，包含 `low_threshold`
- `ManualCriteria`：手动标记条件（无字段）

#### `RuleViolation`

规则违规记录。

**字段：**
- `rule::Rule`：违规的规则
- `timestamp::DateTime`：违规时间戳
- `column::Symbol`：违规的数据列

### 2.4 违规数据类型 (ViolationData)

处理过程违规数据的结构化表示。

**类型层次：**
- `ViolationRule`：单个规则的违规记录（rule_name、count、timestamps）
- `ViolationColumn`：单列的违规汇总（column、total_violations、rules）
- `ViolationSummary`：总体违规统计（total_violations、violation_percentage）
- `ProcessingInfo`：处理过程信息（mast_name、start_time、end_time、total_timestamps）
- `ViolationAnalysisData`：完整的违规分析数据（processing_info、violation_summary、violations_by_column）

### 2.5 代表年校准结果 (RepresentativeYear)

#### `DirectionalCalibration`

方向性校准参数。

**字段：**
- `direction_sector::DirectionSector`：方向扇区
- `slope::Float64`：校准斜率
- `meso_speed_diff::Float64`：中尺度速度差值

#### `CalibrationEachWSSensor`

单个风速传感器的校准结果。

**字段：**
- `target_sensor::SensorColumn`：目标传感器
- `meso_direction_sensor::SensorColumn`：中尺度方向传感器
- `directional_calibrations::Vector{DirectionalCalibration}`：各方向的校准参数

#### `CalibrationResults`

完整校准结果。

**字段：**
- `calibrations::Vector{CalibrationEachWSSensor}`：各传感器校准结果
- `reference_year::DateTime`：参考年份

### 2.6 单测风塔重构结果 (ReconstructSingleMast)

#### `ReconstructionTarget`

重构目标定义。

**字段：**
- `timestamp::DateTime`：需要重构的时间点
- `columns::Vector{Symbol}`：需要重构的列

#### `ReconstructedSuccess`

重构成功记录。

**字段：**
- `timestamp::DateTime`：时间戳
- `columnName::Symbol`：列名
- `value::Float64`：重构值

#### `ReconstructedFailure`

重构失败记录。

**字段：**
- `timestamp::DateTime`：时间戳
- `columnName::Symbol`：列名
- `reason::String`：失败原因

#### `ReconstructionResults`

重构结果汇总。

**字段：**
- `successes::Vector{Dict}`：成功记录列表
- `failures::Vector{Dict}`：失败记录列表

## 3. 配置类型

### 3.1 传感器解析配置 (ParseSensorsConfig)

#### 配置结构层次

- `ParseSensorsConfiguration`：主配置（masts、mesos 数组）
- `ParseSensorsFileConfig`：单个文件配置（input、name、sensor、output、interpolate）
- `SensorFormatConfig`：传感器格式配置（columns、timestamp_column、timestamp_format、delim、skip_to、mappings）
- `SensorColumnConfig`：列解析配置（match、format、patterns）
- `PatternConfig`：正则表达式模式配置
- `MappingRule`：映射规则（match、rule）
- `RuleOutcome`：规则匹配结果
- `InterpolationConfig`：插值配置（from_minutes、to_minutes）

#### 工具函数

- `apply_mapping(rules, input)`：应用映射规则
- `matches_rule(rule, input)`：判断是否匹配规则
- `merge_outcomes(a, b)`：合并两个规则结果

### 3.2 数据清洗配置 (ProcessCleanConfig)

#### `Mast`

单个测风塔的清洗配置。

**字段：**
- `name::String`：测风塔名称
- `input::TimeSeriesSource`：输入数据源
- `output::TimeSeriesSource`：输出数据源
- `rules::Union{String, Array}`：清洗规则（文件路径或内联配置）

#### `ProcessCleanConfiguration`

清洗配置主类型。

**字段：**
- `masts::Vector{Mast}`：测风塔配置列表

**工具函数：**
- `load_rules(rules_config, base_dir)`：加载清洗规则

### 3.3 单测风塔重构配置 (ReconstructSingleConfig)

- `ReconstructSingleMast`：重构配置（name、input、output）
- `ReconstructSingleConfiguration`：主配置（masts 数组）

### 3.4 中尺度训练配置 (TrainMesoConfig)

- `TrainMesoMast`：测风塔训练配置（name、input）
- `TrainMesoSource`：中尺度数据源配置（name、input）
- `TrainMesoModel`：模型定义（mast_name、meso_name、method、output）
- `TrainMesoConfiguration`：主配置（masts、mesos、models 数组）

### 3.5 中尺度重构配置 (ReconstructMesoConfig)

- `ReconstructMesoModelSpec`：模型规格（method、meso_name、model_file）
- `ReconstructMesoModels`：模型集合（windspeed、winddirection）
- `ReconstructMesoMast`：重构配置（name、input、output、time_range、models）
- `ReconstructMesoConfiguration`：主配置（masts、mesos 数组）

### 3.6 代表年校准配置 (RepresentativeYearConfig)

- `RepresentativeYearMesoModel`：中尺度模型配置（method、meso_name、model_file）
- `RepresentativeYearMast`：测风塔校准配置（name、input、output、time_range、meso_model）
- `RepresentativeYearConfiguration`：主配置（masts、mesos 数组）

## 4. 工具函数

### 4.1 通用工具 (Utils)

- `from_dict(::Type{T}, dict)`：从字典创建类型实例
- `to_dict(obj)`：将类型实例转换为字典
- `show_as_dataframe(obj)`：将对象展示为 DataFrame
- `from_disk(paths)`：从磁盘读取对象
- `to_disk(paths, obj)`：将对象写入磁盘
- `strip_nothing_values(d)`：递归移除字典中的 Nothing 值

### 4.2 方向扇区工具 (Sector)

- `DIRECTION_16_SECTORS`：16 方向扇区常量数组
- `get_direction_sector(direction, sectors)`：获取方向对应的扇区
- `degree_diff(a1, a2)`：计算角度差（范围 [-180, 180)）
- `abs_degree_diff(a1, a2)`：计算绝对角度差
- `sector_start(sector)`：获取扇区起始角度
- `sector_end(sector)`：获取扇区结束角度

### 4.3 时间序列处理工具 (TimeSeriesProcessing)

- `Interpolation`：插值模块
- `Regularization`：时间序列正则化模块
- `IntervalDetection`：间隔检测模块
- `MeasurementPeriodCalculator`：测量周期计算模块
- `MastPeriodAlignment`：测风塔周期对齐模块

## 5. 命令模块

### 5.1 解析传感器 (ParseSensors)

- `ColumnParser`：列解析器
- `FileProcessor`：文件处理器
- `DataFrameProcessor`：DataFrame 处理器
- `CommandParseSensors`：命令行接口
- `RecommendParseSensorsCommand`：配置推荐命令

### 5.2 数据清洗 (DataClean)

- `Process`：处理规则模块
- `ProcessTypes`：类型处理模块
- `ProcessRange`：范围检查模块
- `ProcessIcing`：结冰检测模块
- `ProcessLayerDiff`：层差检查模块
- `ProcessAvailability`：可用性检查模块
- `ProcessCleanCommand`：清洗命令
- `RecommendProcessCleanCommand`：配置推荐命令

### 5.3 重构模块

**单测风塔重构 (ReconstructSingleMast)：**
- `GroupByHour`：按小时分组
- `LayerSelection`：层级选择
- `WindSpeedReconstructHourly`：风速重构
- `WindDirectionReconstructHourly`：风向重构
- `ProcessData`：数据处理
- `CommandReconstructSingle`：重构命令
- `RecommendReconstructSingleCommand`：配置推荐命令

**中尺度训练 (TrainMeso)：**
- `Core`：核心模块
- `CommandTrainMeso`：训练命令
- `RecommendTrainMesoCommand`：配置推荐命令

**中尺度重构 (ReconstructMeso)：**
- `Core`：核心模块
- `CommandReconstructMeso`：重构命令
- `RecommendReconstructMesoCommand`：配置推荐命令

**代表年校准 (RepresentativeYear)：**
- `Utils`：工具函数
- `Analysis`：分析模块
- `Core`：核心模块
- `calibrate_to_representative_year`：校准函数
- `CommandRepresentativeYear`：命令行命令
- `RecommendRepresentativeYearCommand`：配置推荐命令
- `ReportGeneration`：报告生成
- `ReportRepresentativeYearCommand`：报告命令

### 5.4 塔影处理 (TowerShading)

- `Core`：核心检测和校正模块
- `CommandTowerShading`：命令行命令
- `RecommendTowerShadingCommand`：配置推荐命令

### 5.5 报告模块

**清洗报告 (ReportClean)：**
- `SensorInventoryReport`：传感器清单报告
- `DataCoverageReport`：数据覆盖报告
- `MonthlyCoverageTable`：月度覆盖表
- `LayerDiffParametersTable`：层差参数表
- `ViolationAnalysisReport`：违规分析报告

**恢复报告 (ReportRecovery)：**
- `RecoveryAnalysis`：恢复分析
- `RecoveryStatusReport`：恢复状态报告

**冻结期报告 (ReportFrozenPeriod)：**
- `PeriodOperations`：期间操作
- `FrozenDetection`：冻结检测
- `MonthlyStatistics`：月度统计
- `ReportGeneration`：报告生成

**重构报告 (ReportReconstructSingle/Meso/Cross)：**
- `DataCoverage`：数据覆盖分析
- `WindSpeedCorrelation`：风速相关性分析
- `WindDirectionDifference`：风向差异分析
- `MonthlyReconstructionTable`：月度重构表
- `AnalysisCore`：分析核心模块
- `DataVisualization`：数据可视化模块
- `ReportGeneration`：报告生成模块

**时间序列报告 (ReportTimeSeries)：**
- `WindRose`：风玫瑰图
- `WindFrequency`：风向频率
- `Weibull`：威布尔分布
- `Turbulence`：湍流分析
- `AirDensity`：空气密度
- `Vertical`：垂直切变
- `Temporal`：时间序列分析
- `FiftyYearsExtremeWind`：50年极值风速

**综合报告 (ReportAllMasts)：**
- `ReportAllMastsCommand`：综合报告命令
- `RecommendReportAllCommand`：配置推荐命令

## 6. 通用导入模式

使用 CleanMast 公共 API 的标准导入模式：

```julia
using CleanMastProject

# 导入类型模块
using .Types: SensorColumns, MastTimeSeries, CleanRules
using .Types.ParseSensorsConfig: ParseSensorsConfiguration
using .Types.ProcessCleanConfig: ProcessCleanConfiguration

# 导入处理模块
using .ParseSensors: CommandParseSensors
using .DataClean: ProcessCleanCommand
using .ReconstructSingleMast: ProcessData
using .MastTimeSeries: load_timeseries, save_timeseries
```

## 7. 文件格式支持

### 7.1 数据文件格式

- **CSV**：需要配套的传感器描述文件（TOML/YAML/JSON）
- **Parquet**：嵌入式传感器元数据（推荐格式）

### 7.2 配置文件格式

- **TOML**：主配置文件格式
- **YAML**：规则文件和结果文件格式
- **JSON**：通用数据交换格式

### 7.3 模型文件格式

- **JLD2**：Julia 序列化格式，用于存储训练模型
