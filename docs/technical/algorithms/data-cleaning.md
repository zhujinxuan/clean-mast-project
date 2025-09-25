# 数据清理算法

## 概述

数据清理是风能数据处理的基础环节，旨在识别和处理测量数据中的异常值、错误和不一致性。CleanMast 采用基于规则的数据清理系统，通过可配置的清理规则检测各种类型的数据异常。

**核心实现位置**：
- 主要清理命令：`src/DataClean/ProcessCleanCommand.jl`
- 配置类型定义：`src/Types/ProcessCleanConfig.jl`
- 规则类型定义：`src/Types/CleanRules.jl`
- 具体规则实现：`src/DataClean/Rules/` 目录下各文件

## 系统架构

### 清理规则系统

CleanMast 采用基于规则的清理系统，每个规则包含：
- **规则类型**：范围检查、层差检查、结冰检测等
- **适用条件**：传感器类型、高度过滤、方向过滤
- **判断标准**：具体的阈值和算法参数
- **处理动作**：标记违规、数据质量分级

**规则定义结构** (`src/Types/CleanRules.jl`)：
```julia
struct Rule
    name::String
    description::String
    sensor_type::String      # "WindSpeed", "WindDirection", "Temperature"
    height_filter::Union{Nothing, Float64}
    direction_filter::Union{Nothing, String}
    criteria::RuleCriteria   # 具体判断标准
end
```

### 处理流程

**数据清理主流程** (`src/DataClean/ProcessCleanCommand.jl`)：
1. 加载清理配置文件 (`process-clean.toml`)
2. 解析清理规则列表
3. 逐一应用每个规则到时间序列数据
4. 收集所有规则违规记录
5. 生成数据质量报告和统计
6. 输出清理后的数据和质量标记

## 具体清理规则实现

### 1. 范围检查规则 (`src/DataClean/Rules/ProcessRange.jl`)

#### 实现原理
检查数据值是否在预设的最小值和最大值范围内。对于缺失值会自动跳过，只检查有效数值。

#### 配置参数
```toml
[[rules]]
name = "风速范围检查"
sensor_type = "WindSpeed"
criteria_type = "Range"
min = 0.0      # 物理最小值
max = 80.0     # 合理最大值（可根据地区调整）

[[rules]]
name = "风向范围检查"
sensor_type = "WindDirection"
criteria_type = "Range"
min = 0.0
max = 360.0

[[rules]]
name = "温度范围检查"
sensor_type = "Temperature"
criteria_type = "Range"
min = -50.0    # 极地最低温
max = 60.0     # 沙漠最高温
```

#### 核心算法实现
```julia
# src/DataClean/Rules/ProcessRange.jl
function apply(rule::Rule, data::TimeSeriesData)::Vector{RuleViolation}
    columns = filter_applicable_columns(rule, data.sensors)
    criteria = rule.criteria

    violations = RuleViolation[]
    for col in columns
        violation_indices = Int[]
        # 检查最小值违规
        if !isnothing(criteria.min)
            append!(violation_indices,
                   findall(x -> !ismissing(x) && x < criteria.min, data.df[!, col]))
        end
        # 检查最大值违规
        if !isnothing(criteria.max)
            append!(violation_indices,
                   findall(x -> !ismissing(x) && x > criteria.max, data.df[!, col]))
        end
        # 生成违规记录
        unique_timestamps = sort(unique(data.df[unique(violation_indices), :timestamp]))
        append!(violations, map(x -> RuleViolation(rule, x, col), unique_timestamps))
    end
    return violations
end
```

#### 推荐阈值
**风速范围** (依据高度和地区调整)：
- 平原地区：0-60 m/s
- 沿海地区：0-70 m/s
- 山地地区：0-80 m/s
- 极地地区：0-90 m/s

**温度范围** (依据地理位置调整)：
- 温带地区：-30°C 到 45°C
- 热带地区：5°C 到 50°C
- 极地地区：-60°C 到 30°C
- 沙漠地区：-10°C 到 60°C

### 2. 结冰检测规则 (`src/DataClean/Rules/ProcessIcing.jl`)

#### 检测原理
结冰会导致传感器响应变慢或完全停止，表现为数值在较长时间内变化极小。通过监测指定时间窗口内的数值变化幅度来识别潜在的结冰影响。

#### 配置参数
```toml
[[rules]]
name = "风速传感器结冰检测"
sensor_type = "WindSpeed"
criteria_type = "Icing"
max_change = 0.02      # 最大允许变化量 (m/s)
time_range = 7200      # 检测时间窗口 (秒，2小时)

[[rules]]
name = "风向传感器结冰检测"
sensor_type = "WindDirection"
criteria_type = "Icing"
max_change = 0.5       # 最大允许变化量 (度)
time_range = 7200      # 检测时间窗口 (秒)
```

#### 核心算法实现
```julia
# src/DataClean/Rules/ProcessIcing.jl
function apply(rule::Rule, data::TimeSeriesData)::Vector{RuleViolation}
    columns = filter_applicable_columns(rule, data.sensors)
    criteria = rule.criteria

    violations = RuleViolation[]
    for col in columns
        values = data.df[!, col]
        timestamps = data.df[!, :timestamp]

        window_start = 1
        while window_start <= length(timestamps)
            value_start = values[window_start]
            if ismissing(value_start)
                window_start += 1
                continue
            end

            # 寻找变化量小于阈值的连续窗口
            window_end = window_start + 1
            while window_end <= length(timestamps)
                value_end = values[window_end]
                if !ismissing(value_end) &&
                   abs(value_end - value_start) > criteria.max_change
                    break
                end
                window_end += 1
            end

            # 检查窗口持续时间是否超过阈值
            window_duration = timestamps[window_end-1] - timestamps[window_start]
            if window_duration >= Second(criteria.time_range)
                # 标记整个窗口为结冰影响
                for i in window_start:(window_end-1)
                    if !ismissing(values[i])
                        push!(violations, RuleViolation(rule, timestamps[i], col))
                    end
                end
            end

            window_start = window_end
        end
    end
    return violations
end
```

#### 结冰检测标准
**风速传感器结冰**：
- 检测窗口：2小时 (7200秒)
- 变化阈值：≤ 0.02 m/s
- 环境条件：温度 ≤ 2°C 且相对湿度 ≥ 85%

**风向传感器结冰**：
- 检测窗口：2小时 (7200秒)
- 变化阈值：≤ 0.5°
- 排除条件：对应风速 < 1 m/s (静风条件下风向本身就稳定)

**温度传感器结冰**：
- 检测窗口：1小时 (3600秒)
- 变化阈值：≤ 0.1°C
- 环境条件：温度在冰点附近 (-2°C 到 2°C)

### 3. 层差检查规则 (`src/DataClean/Rules/ProcessLayerDiff.jl`)

#### 检测原理
比较不同高度间同类型传感器的测量值，检测是否存在不合理的层间差异。对于风向使用圆形差异计算，考虑 0°/360° 边界效应。

#### 配置参数
```toml
[[rules]]
name = "风速层差检查"
sensor_type = "WindSpeed"
criteria_type = "LayerDifference"
max_diff = 15.0           # 最大允许层差 (m/s)
height_diff = 100.0       # 最大检查高度差 (m)
min_lower_wind_speed = 1.0  # 下层最小风速要求

[[rules]]
name = "风向层差检查"
sensor_type = "WindDirection"
criteria_type = "LayerDifference"
max_diff = 45.0           # 最大允许层差 (度)
height_diff = 100.0       # 最大检查高度差 (m)
min_lower_wind_speed = 3.0  # 避免静风条件的最小风速
```

#### 核心算法实现
```julia
# src/DataClean/Rules/ProcessLayerDiff.jl
function apply(rule::Rule, data::TimeSeriesData)::Vector{RuleViolation}
    target_sensors = filter_applicable_columns(rule, data.sensors)
    criteria = rule.criteria
    violations = RuleViolation[]

    for target_col_symbol in target_sensors
        target_sensor = findfirst(s -> s.columnName == target_col_symbol, data.sensors)
        lower_comparisons = find_lower_layer_columns(
            data.sensors[target_sensor], data.sensors, criteria.height_diff
        )

        for comparison in lower_comparisons
            # 检查每个时间点的层差
            for row in eachrow(data.df)
                upper_val = row[target_col_symbol]
                lower_val = row[comparison.lower_col]

                # 跳过缺失值
                if ismissing(upper_val) || ismissing(lower_val)
                    continue
                end

                # 检查风速条件（如果需要）
                if !isnothing(comparison.wind_speed_col) &&
                   !isnothing(criteria.min_lower_wind_speed)
                    wind_speed = row[comparison.wind_speed_col]
                    if ismissing(wind_speed) || wind_speed < criteria.min_lower_wind_speed
                        continue
                    end
                end

                # 计算层差
                diff = calc_difference(upper_val, lower_val,
                                     data.sensors[target_sensor].sensorType)

                # 检查是否超过阈值
                if diff > criteria.max_diff
                    push!(violations, RuleViolation(rule, row.timestamp, target_col_symbol))
                end
            end
        end
    end
    return violations
end

# 差异计算函数
function calc_difference(upper_val::Float64, lower_val::Float64, sensor_type::String)::Float64
    if sensor_type == "WindDirection"
        return abs_degree_diff(upper_val, lower_val)  # 圆形差异
    else
        return abs(upper_val - lower_val)  # 普通差异
    end
end
```

#### 层差检查标准
**风速层差**：
- 最大层差：15 m/s (100m 高度差内)
- 风切变指数范围：0.05 - 0.6
- 检查条件：下层风速 ≥ 1.0 m/s

**风向层差**：
- 最大层差：45° (100m 高度差内)
- 检查条件：下层风速 ≥ 3.0 m/s (避免静风)
- 圆形计算：考虑 350° 与 10° 的实际差异为 20°

**温度层差**：
- 最大层差：5°C (100m 高度差内)
- 理论梯度：6.5°C/km (干绝热递减率)
- 逆温检查：温度随高度增加的异常情况

### 4. 数据可用性规则 (`src/DataClean/Rules/ProcessAvailability.jl`)

#### 检测原理
统计指定时间窗口内的数据可用率，识别数据缺失严重的时间段。这有助于评估数据质量和后续分析的可靠性。

#### 配置参数
```toml
[[rules]]
name = "数据可用性检查"
sensor_type = "WindSpeed"
criteria_type = "Availability"
min_availability = 0.8    # 最小可用率 (80%)
time_window = 3600        # 统计时间窗口 (秒，1小时)
```

#### 算法流程
```julia
# 伪代码：数据可用性检查
function check_availability(data, time_window, min_availability)
    for each time_window in data:
        total_points = expected_points_in_window
        valid_points = count_non_missing_points
        availability_rate = valid_points / total_points

        if availability_rate < min_availability:
            mark_as_low_availability_period
        end
    end
end
```

### 5. 统计异常检测（计划中的规则）

虽然当前系统主要基于物理规则，但计划扩展统计异常检测功能：

#### Z-Score 异常检测
```toml
# 计划中的配置
[[rules]]
name = "风速统计异常检测"
sensor_type = "WindSpeed"
criteria_type = "Statistical"
method = "zscore"
threshold = 3.0           # Z-Score 阈值
window_size = 24          # 计算窗口 (小时)
```

#### IQR 异常检测
```toml
# 计划中的配置
[[rules]]
name = "风速四分位数异常检测"
sensor_type = "WindSpeed"
criteria_type = "Statistical"
method = "iqr"
factor = 1.5              # IQR 倍数因子
window_size = 168         # 计算窗口 (小时，一周)
```

### 6. 塔影检测（独立处理命令）

塔影检测有独立的处理命令 `process tower-shading`，不在常规清理规则中。

#### 实现位置
- 命令实现：`src/TowerShading/ProcessTowerShadingCommand.jl`
- 配置类型：`src/Types/TowerShadingConfig.jl`

#### 检测原理
```toml
# tower-shading.toml 配置示例
[tower_position]
lat = 40.0
lon = 116.0

[shading_params]
shadow_angle_range = 15.0     # 塔影角度范围 (度)
wind_speed_reduction = 0.3    # 风速衰减比例
min_wind_speed = 3.0          # 最小检测风速
```

### 7. 质量控制输出

#### 违规记录结构
```julia
# src/Types/CleanRules.jl
struct RuleViolation
    rule::Rule              # 违规的规则
    timestamp::DateTime     # 违规时间戳
    column::Symbol         # 违规的数据列
end
```

#### 清理统计报告
处理完成后系统会自动生成：
1. **总体统计**：总数据点数、有效数据数、违规数据数、数据可用率
2. **规则统计**：每个规则的违规次数和比例
3. **传感器统计**：每个传感器/高度的数据质量评分
4. **时间分布**：违规数据的时间分布模式

#### 输出文件
- `cleaned_data.csv`: 清理后的时间序列数据
- `violations.csv`: 详细的违规记录列表
- `cleaning_statistics.json`: 清理统计和质量评估
- `data_quality_flags.csv`: 每个数据点的质量标记

### 8. 配置文件管理

#### 配置生成命令
使用 `recommend process-clean` 命令可以自动生成配置模板：

```bash
julia bin/CleanMast.jl recommend process-clean --project-dir /path/to/project
```

#### 标准配置模板
```toml
# process-clean.toml 完整示例
[input]
data_file = "parsed_data.csv"
sensors_file = "sensors.toml"

[output]
data_file = "cleaned_data.csv"
violations_file = "violations.csv"
statistics_file = "cleaning_statistics.json"
flags_file = "data_quality_flags.csv"

# 风速范围检查
[[rules]]
name = "WindSpeed Range Check"
sensor_type = "WindSpeed"
criteria_type = "Range"
min = 0.0
max = 80.0

# 风向范围检查
[[rules]]
name = "WindDirection Range Check"
sensor_type = "WindDirection"
criteria_type = "Range"
min = 0.0
max = 360.0

# 风速结冰检测
[[rules]]
name = "WindSpeed Icing Detection"
sensor_type = "WindSpeed"
criteria_type = "Icing"
max_change = 0.02
time_range = 7200

# 风速层差检查
[[rules]]
name = "WindSpeed Layer Difference"
sensor_type = "WindSpeed"
criteria_type = "LayerDifference"
max_diff = 15.0
height_diff = 100.0
min_lower_wind_speed = 1.0

# 风向层差检查
[[rules]]
name = "WindDirection Layer Difference"
sensor_type = "WindDirection"
criteria_type = "LayerDifference"
max_diff = 45.0
height_diff = 100.0
min_lower_wind_speed = 3.0

# 数据可用性检查
[[rules]]
name = "Data Availability Check"
sensor_type = "WindSpeed"
criteria_type = "Availability"
min_availability = 0.8
time_window = 3600
```

## 数据质量分级和处理策略

### 质量标记系统

CleanMast 不删除数据，而是为每个数据点分配质量标记：

```julia
# 质量等级定义
enum DataQuality
    EXCELLENT = 1    # 优质：无任何违规
    GOOD = 2         # 良好：轻微违规
    ACCEPTABLE = 3   # 可接受：中等违规，可用但需谨慎
    SUSPICIOUS = 4   # 可疑：严重违规，建议排除
    INVALID = 5      # 无效：极严重违规，不应使用
end
```

### 违规严重性评估

不同规则的违规对数据质量的影响程度不同：

| 规则类型 | 轻微违规 | 中等违规 | 严重违规 |
|----------|----------|----------|----------|
| 范围检查 | 超出 5% | 超出 20% | 超出 50% |
| 层差检查 | 超出阈值 10% | 超出阈值 50% | 超出阈值 100% |
| 结冰检测 | 1-2小时持续 | 2-6小时持续 | >6小时持续 |
| 可用性检查 | 75-80% 可用 | 50-75% 可用 | <50% 可用 |

### 多规则综合评估

当多个规则同时违规时，系统采用加权评分方式：

```julia
# 伪代码：质量等级计算
function calculate_quality_level(violations_for_timestamp)
    total_penalty = 0

    for violation in violations_for_timestamp
        rule_weight = get_rule_weight(violation.rule)
        severity = calculate_severity(violation)
        total_penalty += rule_weight * severity
    end

    return classify_quality_level(total_penalty)
end
```

## 参数调优指导

### 环境特定参数调整

不同环境条件需要调整相应的阈值参数：

**海上风场**：
- 风速上限：提高到 90 m/s
- 层差阈值：适当放宽 (±20%)
- 结冰检测：禁用或调整阈值

**山地地形**：
- 风速上限：提高到 100 m/s
- 层差阈值：显著放宽 (±50%)
- 风向层差：放宽到 60°

**城市环境**：
- 风速上限：降低到 60 m/s
- 层差阈值：收紧 (-20%)
- 增加湍流强度检查

**极地地区**：
- 温度范围：扩展到 -60°C 到 30°C
- 结冰检测：降低阈值，延长时间窗口
- 风速层差：考虑极地逆温层

### 季节性参数调整

```toml
# 季节性配置示例
[[rules]]
name = "Temperature Range Check - Winter"
sensor_type = "Temperature"
height_filter = 10.0
criteria_type = "Range"
min = -40.0     # 冬季更低的最低温度
max = 25.0      # 冬季更低的最高温度
season_filter = "winter"    # 计划中的功能

[[rules]]
name = "Temperature Range Check - Summer"
sensor_type = "Temperature"
height_filter = 10.0
criteria_type = "Range"
min = -10.0     # 夏季较高的最低温度
max = 50.0      # 夏季更高的最高温度
season_filter = "summer"    # 计划中的功能
```

## 扩展开发指导

### 添加新的清理规则

1. **定义新的判断标准类型** (`src/Types/CleanRules.jl`)：
```julia
struct NewCriteria <: RuleCriteria
    parameter1::Float64
    parameter2::Int
    # 其他参数
end
```

2. **实现规则处理模块** (`src/DataClean/Rules/ProcessNewRule.jl`)：
```julia
module ProcessNewRule
using ....Types.CleanRules: Rule, RuleViolation, NewCriteria

function apply(rule::Rule, data::TimeSeriesData)::Vector{RuleViolation}
    @assert rule.criteria isa NewCriteria
    # 实现具体的检测逻辑
    return violations
end

export apply
end
```

3. **在主处理模块中注册** (`src/DataClean/Rules/Process.jl`)：
```julia
if criteria isa NewCriteria
    return ProcessNewRule.apply(rule, data)
end
```

### 性能优化建议

1. **大数据集处理**：
   - 使用 `@threads` 并行处理多个传感器
   - 分批加载和处理数据
   - 利用 Julia 的向量化操作

2. **内存优化**：
   - 及时释放不需要的中间结果
   - 使用 `missing` 而不是 `NaN` 表示缺失值
   - 考虑使用更紧凑的数据类型

3. **算法优化**：
   - 预先过滤适用的列，减少重复计算
   - 缓存重复使用的计算结果
   - 使用早期退出策略减少不必要的检查

通过基于规则的清理系统，CleanMast 提供了灵活、可配置、可扩展的数据质量控制方案，确保风能数据分析的可靠性和准确性。