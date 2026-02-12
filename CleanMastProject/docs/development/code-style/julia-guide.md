# CleanMast Julia 代码风格指南

本文档定义了 CleanMast 项目的 Julia 编码规范。所有贡献者应遵循这些规范以保持代码库的一致性和可维护性。

## 1 代码格式

### 1.1 缩进与空格

- 使用 **4 个空格** 进行缩进，不使用制表符
- 单行代码最大长度 **92 个字符**
- 函数参数列表中的逗号后添加空格

```julia
function process_wind_data(data::DataFrame, config::ProcessCleanConfig)::DataFrame
    validate_data_format(data)
    return apply_processing_rules(data, config)
end
```

### 1.2 空格规范

- 运算符两侧添加空格（`.` 除外）
- 冒号 `:` 两侧不加空格（类型注解除外）
- 关键字参数使用 **分号** 分隔

```julia
# 正确
Position(; line=1, character=0)
wind_speed_data .|> speed -> 0.5 * 1.225 * speed^3

# 错误
Position(;line=1,character=0)  # 缺少空格
```

### 1.3 括号使用

- 函数调用时括号紧贴函数名，不加空格
- 类型注解使用 `::` 时不加空格

```julia
# 正确
df[:, :timestamp]
filter(row -> !ismissing(row.wind_speed), data)

# 错误
df [:, : timestamp]  # 括号内多余空格
```

## 2 命名规范

### 2.1 函数命名

- 使用 **小写字母加下划线**（snake_case）
- 名称应清晰表达函数功能
- 避免缩写（除非是广泛认可的缩写）

```julia
# 正确
find_nearest_height_sensor
validate_data_format
process_wind_speed

# 避免
find_nearest  # 含义不明确
proc_wind  # 过度缩写
```

### 2.2 类型命名

- 结构体和抽象类型使用 **首字母大写的驼峰命名**（PascalCase）
- 配置类型以 `Config` 结尾
- 传感器相关类型清晰表达其用途

```julia
# 正确
struct SensorColumn
    columnName::Symbol
    sensorType::String
    height::Float64
end

struct ProcessCleanConfig
    range_valid::Bool
    layer_diff_check::Bool
end
```

### 2.3 模块命名

- 使用 **首字母大写的驼峰命名**
- 模块名应反映其功能领域

```julia
module SensorColumns
module DataClean
module ReconstructMeso
```

### 2.4 变量命名

- 局部变量使用 **snake_case**
- 避免单字符变量名（循环计数器除外）
- 布尔变量使用 `is_`、`has_`、`needs_` 前缀

```julia
# 正确
wind_speed_data = 12.5
is_valid_range = true
needs_processing = false

# 循环中的索引变量
for i in eachindex(sensors)
```

## 3 类型安全

### 3.1 函数类型签名

- 为所有公共函数添加 **返回类型注解**
- 使用具体类型而非抽象类型

```julia
# 推荐
function process_data(df::DataFrame)::DataFrame
    return filter(row -> !ismissing(row.value), df)
end

# 避免 - 返回类型过于宽泛
function process_data(df)  # 缺少类型信息
```

### 3.2 参数类型限制

- 对函数参数使用 ** restrictive type constraints**
- 使用 Union 类型处理可选值

```julia
# 推荐 - 明确的类型限制
function find_sensor(
    sensors::Vector{SensorColumn},
    height::Float64
)::Union{SensorColumn, Nothing}
    return find_nearest_height_sensor(height, sensors, "WindSpeed", "avg")
end

# 避免 - 类型过于宽泛
function find_sensor(sensors, height)  # 类型不明确
```

### 3.3 结构体字段类型

- 为所有结构体字段指定具体类型
- 使用适当的默认值

```julia
@with_kw struct ProcessingConfig
    enabled::Bool = true
    threshold::Float64 = 0.95
    max_gap_hours::Int = 24
end
```

## 4 数据处理模式

### 4.1 Symbol 与 String 的使用

**关键规则**：Julia DataFrames 要求使用 **Symbol** 进行列操作，而非 String。

```julia
# 正确 - 使用 Symbol
select(df, :wind_speed, :wind_direction)
df[:, :timestamp]
filter(:wind_speed => x -> x > 3.0, df)

# 错误 - 使用 String（会导致错误）
select(df, "wind_speed", "wind_direction")  # 运行时错误
df[:, "timestamp"]

# 动态列名转换
col_name = "wind_speed_80m"
df[:, Symbol(col_name)]  # 将字符串转换为 Symbol
```

### 4.2 方法链式调用

使用管道运算符 `|>` 构建清晰的数据处理流程：

```julia
cleaned_data = raw_data |>
    df -> filter(:wind_speed => x -> !ismissing(x) && x >= 0, df) |>
    df -> select(df, :timestamp, :wind_speed, :wind_direction) |>
    df -> transform(df, :wind_speed => ByRow(x -> x * 1.0) => :wind_speed)
```

### 4.3 向量化操作

优先使用广播和向量化操作，避免循环：

```julia
# 推荐 - 向量化
wind_power = wind_speed_data .|> speed -> 0.5 * 1.225 * speed^3
mean_speed = mean(skipmissing(wind_speed_data))

# 避免 - 循环处理
wind_power = Float64[]
for speed in wind_speed_data
    if !ismissing(speed)
        push!(wind_power, 0.5 * 1.225 * speed^3)
    end
end
```

### 4.4 DataFrame 子集操作

使用标准索引语法进行数据子集操作：

```julia
# 正确 - 标准索引
subset_data = full_data[1:1000, :]
filtered_data = filter(:value => x -> x > threshold, df)

# 使用 ! 符号进行原地操作（谨慎使用）
select!(df, :col1, :col2)
```

## 5 函数式编程风格

### 5.1 避免 push! 模式

**核心原则**：优先使用 `filter`、`map`、`reduce` 等函数式操作，避免使用 `push!` 构建结果。

```julia
# 错误 -  imperative 风格
results = DataFrame()
for row in eachrow(data)
    if row.wind_speed > threshold
        push!(results, row)
    end
end

# 正确 - 函数式风格
results = filter(row -> row.wind_speed > threshold, data)

# 错误 - 构建数组
wind_speeds = Float64[]
for sensor in sensors
    if sensor.sensorType == "WindSpeed"
        push!(wind_speeds, sensor.height)
    end
end

# 正确 - 函数式风格
wind_speeds = sensors |>
    s -> filter(ss -> ss.sensorType == "WindSpeed", s) |>
    s -> map(ss -> ss.height, s)

# 正确 - 列表推导式
wind_speeds = [s.height for s in sensors if s.sensorType == "WindSpeed"]
```

### 5.2 使用 zip 进行并行迭代

```julia
# 正确 - zip 配合 map
height_speed_pairs = collect(zip(heights, speeds))
processed_pairs = map(((h, s),) -> process_measurement(h, s), height_speed_pairs)

# 避免 - 嵌套循环
processed_pairs = []
for (h, s) in zip(heights, speeds)
    push!(processed_pairs, process_measurement(h, s))
end
```

### 5.3 使用 DataFrame 连接替代循环

```julia
# 正确 - 使用 join
combined_data = leftjoin(mast_data, meso_data; on = :timestamp)

# 避免 - 手动循环合并
```

## 6 缺失值处理

### 6.1 基本原则

- 使用 `ismissing()` 检查缺失值
- 让缺失值自然传播，不强制填充
- 使用 `skipmissing()` 进行统计计算

```julia
# 检查缺失
if ismissing(value)
    return nothing
end

# 统计计算时跳过缺失
mean_speed = mean(skipmissing(wind_speed_data))

# 过滤缺失行
valid_data = filter(row -> !ismissing(row.wind_speed), df)
```

### 6.2 条件过滤

在过滤条件中显式处理缺失值：

```julia
# 明确处理缺失的过滤
valid_records = filter(:value => x -> !ismissing(x) && x > 0, df)
```

## 7 注释与文档

### 7.1 注释原则

- **最小化注释**：仅在真正必要时添加注释
- **自文档化代码**：使用清晰的函数和变量名替代注释
- **注释原因而非内容**：解释为什么这样做，而非在做什么

```julia
# 推荐 - 清晰命名减少注释
function validate_wind_speed_range(speed::Float64)::Bool
    return speed >= 0.0 && speed <= 50.0
end

# 仅在非显而易见的场景添加注释
# 80m 高度的数据用于轮毂高度外推
reference_sensor = find_nearest_height_sensor(80.0, sensors, "WindSpeed")
```

### 7.2 文档字符串

为公共 API 函数添加文档字符串：

```julia
"""
    find_nearest_height_sensor(
        target_height::Float64,
        sensors::Vector{SensorColumn},
        sensor_type::String,
        stat_type::String="avg"
    )::Union{SensorColumn, Nothing}

在传感器列表中查找指定类型的最近高度传感器。

# 参数
- `target_height`: 目标高度（米）
- `sensors`: 传感器列表
- `sensor_type`: 传感器类型（如 "WindSpeed"）
- `stat_type`: 统计类型，默认为 "avg"

# 返回
匹配到的最近传感器，未找到时返回 `nothing`
"""
function find_nearest_height_sensor(...)::Union{SensorColumn, Nothing}
    # 实现
end
```

### 7.3 领域上下文注释

仅在涉及气象或物理约束时添加注释：

```julia
# 风功率密度计算：ρ = 1.225 kg/m³（标准大气压下）
power_density = 0.5 * 1.225 * speed^3
```

## 8 测试规范

### 8.1 测试结构

- 使用 `Test` 标准库
- 使用 `@testset` 组织测试用例
- 为每个模块创建独立测试文件

```julia
using Test

@testset "Wind Speed Processing" begin
    @test process_wind_speed(10.0) ≈ 10.0
    @test ismissing(process_wind_speed(missing))
end
```

### 8.2 测试原则

- 包含正向和负向测试用例
- 测试边界条件和异常情况
- 使用 `fixtures/` 目录管理复杂测试数据

### 8.3 运行测试

```bash
# 运行所有测试
julia CleanMastProject/test/runtests.jl

# 运行特定模块测试
julia CleanMastProject/test/runtests.jl DataClean

# 查看可用测试集
julia CleanMastProject/test/runtests.jl --help
```

## 9 反模式

### 9.1 避免的代码模式

**模式 1：硬编码列名**

```julia
# 错误 - 硬编码列名
data = df[:, :wind_speed_80m]  # 脆弱！

# 正确 - 使用传感器元数据
function get_sensor_data(df::DataFrame, sensor::SensorColumn)
    return df[:, sensor.columnName]
end
```

**模式 2：类型宽泛的函数签名**

```julia
# 错误 - 类型过于宽泛
function process(data)  # 任意类型
    # ...
end

# 正确 - 具体类型
function process(data::DataFrame)::DataFrame
    # ...
end
```

**模式 3：过度使用 Any 类型**

```julia
# 错误 - 使用 Any
config::Any  # 失去类型检查优势

# 正确 - 具体类型
config::ProcessingConfig
```

**模式 4：缺少返回值类型注解**

```julia
# 错误 - 缺少返回类型
function calculate_mean(speeds::Vector{Float64})
    return sum(speeds) / length(speeds)
end

# 正确 - 添加返回类型
function calculate_mean(speeds::Vector{Float64})::Float64
    return sum(speeds) / length(speeds)
end
```

### 9.2 正确的代码模式

**配置加载模式**

```julia
function load_config(config_path::String)::ConfigType
    config_dict = TOML.parsefile(config_path)
    return ConfigType(; config_dict...)
end
```

**数据处理管道模式**

```julia
function process_stage(input_data::DataFrame, config::StageConfig)::DataFrame
    validate_data_format(input_data)

    result = input_data |>
        df -> apply_quality_filters(df, config) |>
        df -> apply_corrections(df, config)

    validate_processing_results(result)
    return result
end
```

**传感器查找模式**

```julia
# 过滤传感器 - 使用 filter
wind_sensors = filter(
    s -> s.sensorType ∈ ["WindSpeed", "WindDirection"] && s.statType == "avg",
    sensors
)

# 查找最近高度
target_sensor = find_nearest_height_sensor(80.0, wind_sensors, "WindSpeed")
```

## 10 快速参考

| 规范类别 | 规则 |
|---------|------|
| 缩进 | 4 空格 |
| 行长度 | 92 字符 |
| 函数命名 | snake_case |
| 类型命名 | PascalCase |
| 列操作 | 使用 Symbol |
| 数组构建 | 避免 push!，使用推导式 |
| 参数分隔 | 关键字参数使用 `;` |
| 返回类型 | 显式声明返回类型 |
| 注释 | 最小化，仅必要时添加 |

遵循这些规范可确保 CleanMast 代码库的一致性、可读性和可维护性。如有疑问，请参考现有源代码或 AGENTS.md 文件。
