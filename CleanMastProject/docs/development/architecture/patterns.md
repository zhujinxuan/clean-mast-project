# CleanMast 设计模式

本文档描述 CleanMast 项目中使用的核心设计模式，帮助开发者理解架构决策。

## 概述

CleanMast 采用函数式编程风格，结合类型驱动的设计，确保代码的可维护性和可扩展性。项目遵循以下核心原则：

- 不可变配置
- 纯函数优先
- 管道式数据处理
- 类型安全的配置解析

## 1. 命令模式 (Command Pattern)

### 模式说明

CleanMast 使用 Comonicon.jl 实现命令行接口，每个处理步骤都有独立的命令模块。命令模式将操作封装为对象，支持灵活的参数传递和执行。

### 典型结构

```
Command 模块
├── execute(config_path::String)  # 入口函数
├── recommend(dir::String)         # 配置生成函数
└── 辅助函数
```

### 示例位置

- `CleanMastProject/src/Command/ProcessSteps.jl` - 管道步骤命令
- `CleanMastProject/src/DataClean/ProcessCleanCommand.jl` - 数据清理命令
- `CleanMastProject/src/DataClean/RecommendProcessCleanCommand.jl` - 配置推荐命令

### 使用方式

```bash
# 执行数据清理
julia bin/CleanMast.jl process clean --config process-clean.toml

# 推荐配置
julia bin/CleanMast.jl recommend clean
```

## 2. 配置模式 (Configuration Pattern)

### 模式说明

CleanMast 使用 TOML 格式的配置文件管理所有处理参数。配置系统采用分层设计：原始配置（带路径引用）经过规范化后转换为标准化配置（包含绝对路径和完整结构）。

### 配置结构层次

```
ParseSensorsConfiguration（原始配置）
├── ParseSensorsFileConfig
│   ├── input::String                    # 输入文件路径
│   ├── sensor::Union{String, SensorFormatConfig}  # 传感器配置
│   └── output::TimeSeriesSource         # 输出配置
│
└── ParseSensorsConfigurationNormalized（规范化配置）
    └── 所有路径均为绝对路径
```

### 规范与反规范

每个配置类型都实现 `from_dict` 和 `to_dict` 函数：

```julia
# 从字典创建配置（TOML 解析）
from_dict(::Type{ParseSensorsConfiguration}, dict::Dict{String, Any})

# 导出为字典
to_dict(psc::ParseSensorsConfiguration)::Dict{String, Any}
```

### 示例位置

- `CleanMastProject/src/Types/ParseSensorsConfig.jl` - 解析配置类型定义
- `CleanMastProject/src/Types/ProcessCleanConfig.jl` - 清理配置类型定义

## 3. 管道模式 (Pipeline Pattern)

### 模式说明

数据处理采用管道模式，将复杂处理分解为多个独立步骤，每个步骤专注于特定功能。步骤之间通过配置文件传递状态，支持选择性执行和断点续传。

### 处理步骤结构

```
ProcessingStep（步骤定义）
├── number::Int                    # 步骤编号
├── name::String                   # 步骤名称
├── description::String            # 描述
├── execute_func::Function         # 执行函数
├── config_file::Union{String, Nothing}  # 配置文件
├── output_check::Union{String, Nothing} # 输出检查路径
└── conditional::Bool              # 是否条件执行
```

### 完整处理流程

1. **recommend-clean** - 生成数据清理配置
2. **clean** - 执行数据清理
3. **recommend-tower-shading** - 生成塔影校正配置
4. **tower-shading** - 执行塔影校正
5. **recommend-reconstruct-single** - 生成单塔重构配置
6. **reconstruct-single** - 执行单塔重构
7. **recommend-train-cross** - 生成跨塔训练配置
8. **train-cross** - 训练跨塔模型
9. **recommend-reconstruct-cross** - 生成跨塔重构配置
10. **reconstruct-cross** - 执行跨塔重构
11. **recommend-train-meso** - 生成中尺度训练配置
12. **train-meso** - 训练中尺度模型
13. **recommend-reconstruct-meso** - 生成中尺度重构配置
14. **reconstruct-meso** - 执行中尺度重构
15. **recommend-representative-year** - 生成代表年配置
16. **representative-year** - 校准代表年
17. **recommend-wt-timeseries** - 生成风机型时间序列配置
18. **wt-timeseries** - 生成 WT 时间序列

### 示例位置

`CleanMastProject/src/Command/ProcessSteps.jl` - 定义所有处理步骤

## 4. 类型安全配置模式 (Type-Safe Configuration)

### 模式说明

CleanMast 使用 Julia 的类型系统确保配置的正确性。每个配置类型都是不可变结构体（struct），字段具有明确的类型约束。

### 类型定义示例

```julia
# 配置结构体使用具体类型
struct Mast
    name::String
    input::TimeSeriesSource
    output::TimeSeriesSource
    rules::Union{String, Array}
end

# 规则结果使用联合类型处理可选值
struct RuleOutcome
    sensorType::Union{String, Nothing}
    sensorDirection::Union{String, Nothing}
    height::Union{Float64, Nothing}
    statType::Union{String, Nothing}
    unit::Union{String, Nothing}
    multiplier::Union{Float64, Nothing}
end
```

### 类型检查优势

- 编译期错误检测
- IDE 智能提示
- 配置文件验证
- 文档自动生成

### 示例位置

- `CleanMastProject/src/Types/` - 所有配置类型定义
- `CleanMastProject/src/Types/SensorColumns.jl` - 传感器列类型

## 5. 函数式数据处理模式

### 模式说明

CleanMast 遵循函数式编程风格，避免使用带副作用的循环，使用管道操作符组合转换函数。

### 推荐模式

```julia
# 使用管道组合转换
cleaned_data = raw_data |>
    df -> filter(row -> !ismissing(row.wind_speed), df) |>
    df -> select(df, :timestamp, :wind_speed, :wind_direction)

# 使用函数式过滤
valid_records = filter(row -> row.wind_speed > threshold, data)

# 使用 map 进行转换
heights = sensors |>
    sensors -> filter(s -> s.sensorType == "WindSpeed", sensors) |>
    sensors -> map(s -> s.height, sensors)
```

### 应避免的模式

```julia
# 错误：使用 push! 构建结果
results = DataFrame()
for row in eachrow(data)
    if row.wind_speed > threshold
        push!(results, row)
    end
end

# 正确：使用 filter
results = filter(row -> row.wind_speed > threshold, data)
```

## 6. 映射规则模式 (Mapping Rule Pattern)

### 模式说明

传感器列解析使用规则映射模式，通过匹配条件和结果转换定义灵活的列名解析逻辑。

### 规则结构

```
MappingRule（映射规则）
├── match::Dict{String, Union{Nothing, Float64, String}}  # 匹配条件
└── rule::RuleOutcome                                      # 匹配结果
```

### 功能函数

```julia
# 检查输入是否匹配规则
matches_rule(rule::MappingRule, input::Dict{String, Any})::Bool

# 应用规则链
apply_mapping(rules::Vector{MappingRule}, input::Dict{String, Any})::RuleOutcome

# 合并规则结果
merge_outcomes(a::RuleOutcome, b::RuleOutcome)::RuleOutcome
```

### 示例位置

`CleanMastProject/src/Types/ParseSensorsConfig.jl` - 映射规则实现

## 7. 配置验证模式

### 模式说明

配置加载后经过验证，确保必需字段存在且类型正确。

### 验证流程

```julia
function load_config(config_path::String)::ConfigType
    config_dict = TOML.parsefile(config_path)
    return from_dict(ConfigType, config_dict)
end
```

### 推荐配置生成

使用 `recommend` 命令生成带默认值的配置文件：

```bash
julia bin/CleanMast.jl recommend clean      # 数据清理配置
julia bin/CleanMast.jl recommend tower-shading  # 塔影校正配置
```

## 模式组合使用

### 典型工作流

```
1. 命令入口
   └─> Command.execute(config_path)

2. 配置加载
   └─> from_dict(ConfigType, TOML.parsefile(config_path))

3. 配置规范化
   └─> from_dict(ConfigTypeNormalized, to_dict(raw_config))

4. 数据处理管道
   └─> input_data |> transform1 |> transform2 |> ...

5. 结果验证
   └─> validate_processing_results(result)
```

### 示例位置

完整工作流示例参见 `CleanMastProject/src/Command/ProcessSteps.jl`

## 设计原则

### 不可变性

所有配置结构体均为不可变（`struct`），修改配置需创建新实例：

```julia
# 正确：返回新实例
function with_height(config::SensorConfig, new_height::Float64)
    return SensorConfig(new_height, config.other_fields...)
end
```

### 纯函数

优先使用无副作用的纯函数：

```julia
# 纯函数：仅依赖输入，返回新值
function normalize_wind_speed(speed::Float64, multiplier::Float64)
    return speed * multiplier
end

# 非纯函数：修改全局状态（应避免）
function process_with_side_effects!(data::DataFrame)
    global PROCESSED_COUNT += 1
    # ...
end
```

### 单一职责

每个模块专注于特定功能：

- `ParseSensorsConfig` - 传感器解析配置
- `ProcessCleanConfig` - 数据清理配置
- `ReconstructSingleConfig` - 单塔重构配置

## 扩展指南

### 添加新配置类型

1. 在 `CleanMastProject/src/Types/` 下创建新文件
2. 定义不可变结构体
3. 实现 `from_dict` 和 `to_dict` 函数
4. 导出类型和构造函数

### 添加新处理步骤

1. 在对应模块中实现 `execute` 和 `recommend` 函数
2. 在 `ProcessSteps.jl` 中添加 `ProcessingStep` 定义
3. 更新命令注册

## 总结

CleanMast 的设计模式组合实现了：

- **可测试性** - 纯函数和不可变数据便于单元测试
- **可维护性** - 清晰的模块边界和职责划分
- **可扩展性** - 新功能通过添加配置和步骤实现
- **类型安全** - Julia 类型系统确保配置正确性
