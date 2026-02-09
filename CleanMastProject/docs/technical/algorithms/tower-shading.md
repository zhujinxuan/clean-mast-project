# 塔影检测与校正算法

## 算法概述

塔影检测与校正算法用于识别和处理气象测风塔结构对风速测量的影响。当风速传感器安装在格构式塔架上时，塔架结构会对来风方向上的传感器产生遮蔽效应，导致测量的风速值低于实际自由流风速。该算法通过合并同一高度层上多个传感器的测量值，选择受塔影影响最小的数据，从而提高风速测量的准确性。

## 核心原理

格构式测风塔在风的作用下会在其背风面形成尾流区，尾流区内的风速相比自由流风速显著降低。安装在塔架上的传感器如果处于尾流区内，其测量值将被低估。由于塔架对不同风向的遮蔽效应不同，位于塔架不同方位的传感器会交替受到塔影影响。该算法利用这一特性，通过比较同一高度层上多个传感器的测量值，识别并排除受塔影影响的数据点。

## 适用场景

该算法适用于以下情况：

- 测风塔采用格构式塔架结构而非桁架式或独立式桅杆
- 同一高度层安装有多个风速传感器，分布于塔架的不同方位
- 需要提高风速测量数据的质量，为后续风资源评估提供可靠数据
- 数据中存在由于塔架遮蔽导致的系统性偏低测量值

## 实现细节

### 核心处理逻辑

塔影校正算法的核心实现位于 `src/TowerShading/Core.jl`，仅处理 `WindSpeed` 类型传感器，不处理 `WindDirection` 传感器。

#### 高度匹配算法

```julia
function find_nearby_sensors(
    sensorType::String,
    sensors::Vector{SensorColumn}, 
    target_height::Float64, 
    max_diff::Float64=2.0  # 默认值
)::Vector{Int}
```

**高度匹配规则**：
- 传感器高度差在 `2.0米` 以内视为同一高度层
- 仅匹配 `sensorType == "WindSpeed"` 的传感器
- 返回满足条件的所有传感器索引

#### 优选高度选择

```julia
function get_preferred_height(heights::Vector{Float64})::Float64
    mean_height = mean(heights)
    divisible_by_10 = filter(h -> h % 10 ≈ 0, heights)
    
    if !isempty(divisible_by_10)
        return divisible_by_10[argmin(abs.(divisible_by_10 .- mean_height))]
    end
    
    return round(mean_height)
end
```

**高度选择策略**：
1. 从候选高度中查找 10 的倍数
2. 若存在 10 的倍数，选择最接近平均值的那一个
3. 若不存在 10 的倍数，将平均值四舍五入到最近整数

#### 传感器合并策略

```julia
function calculate_max_between_columns(df::DataFrame, cols::Vector{Symbol})
    # 对每行数据，取所有列中的最大值
    # missing 值被忽略（视为不存在）
    # 若所有值均为 missing，则返回 missing
    return maximum(non_missing_values)
end
```

**合并规则**：
- 对每行数据，从多个同高度传感器中取 **最大值**
- missing 值不参与比较（相当于跳过）
- 仅当所有传感器值均为 missing 时，结果才为 missing

#### 输出传感器命名

```julia
function create_merged_sensor(stat_sensors, preferred_height)
    height_str = format_height(preferred_height)  # 整数显示为整数，否则保留1位小数
    new_name = "$(sensorType)_$(height_str)m_$(statType)_$(unit)"
end
```

**命名格式**：`{sensorType}_{height}m_{statType}_{unit}`

**示例**：
- `WindSpeed_80m_avg_m/s`
- `WindSpeed_43.5m_avg_m/s`

### 默认参数值

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_diff` | `2.0` | 高度匹配容差（米），超过此值视为不同高度 |
| `height_multiples_of_10` | 优先选择 | 高度优选策略，优先 10 的倍数 |

### 处理流程（代码级）

```
1. 筛选 WindSpeed 传感器
2. 遍历所有唯一高度
3. 查找该高度 ±2.0m 范围内的所有 WindSpeed 传感器
4. 按 statType 分组
5. 每组内：
   a. 选择优选高度（优先 10 的倍数，否则平均值取整）
   b. 创建新传感器记录（命名格式：{type}_{height}m_{stat}_{unit}）
   c. 对每行数据取最大值合并
6. 删除原始传感器列
7. 更新传感器列表
```

## 配置示例

```toml
# tower-shading.toml

[[masts]]
name = "PN-MAST-01"

[masts.input]
data = "processed/PN-MAST-01_timeseries.parquet"
sensors = "processed/PN-MAST-01_sensors.toml"

[masts.output]
data = "processed/PN-MAST-01_timeseries_shading.parquet"
sensors = "processed/PN-MAST-01_sensors_shading.toml"
```

配置结构定义于 `src/Types/TowerShadingConfig.jl`：

```julia
struct TowerShadingMast
    name::String
    input::TimeSeriesSource
    output::TimeSeriesSource
end

struct TowerShadingConfiguration
    masts::Vector{TowerShadingMast}
end
```

## 默认推荐值

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| 高度匹配容差 | `2.0` 米 | 适用于标准测风塔，传感器高度差在此范围内合并 |
| 高度优选策略 | 优先 10 的倍数 | 如 40m、50m、80m 等标准高度 |
| 合并策略 | 取最大值 | 保留自由流条件下的最高风速值 |
| 适用传感器类型 | 仅 WindSpeed | WindDirection 不参与塔影校正 |

## 输入数据

塔影校正处理需要以下输入数据：

- **时间序列数据**：包含时间戳、风速测量值及相关统计量的表格数据
- **传感器配置**：各传感器的安装高度、传感器类型、统计类型等信息
- **处理配置**：定义输入数据源和输出数据源的文件路径

配置文件中需要指定参与塔影处理的各个测风塔名称、对应的输入文件路径和输出文件路径。

## 输出结果

塔影校正处理生成以下输出：

- **校正后的时间序列数据**：经过塔影校正处理的时间序列数据
- **合并后的传感器记录**：从多个同高度传感器合并而成的单一传感器记录
- **数据质量标记**：标识哪些数据点受到塔影影响

## 处理效果

经过塔影校正处理后，数据将呈现以下改善：

- 消除或减少由于塔架遮蔽导致的系统性偏低测量值
- 提高风速测量的代表性和可靠性
- 为后续的风速频率分布分析、风功率密度计算等提供更准确的数据基础
- 改善不同高度层风速数据之间的一致性
