# recommend process-clean

## 概述

生成数据清理处理的配置文件，为数据质量控制和异常值检测创建初始配置。

## 语法

```bash
julia bin/CleanMast.jl recommend process-clean <项目目录>
```

## 实现位置

**核心实现**: `src/DataClean/RecommendProcessCleanCommand.jl`

## 功能流程

1. **数据源识别**
   - 读取 `parse-sensors.toml` 文件
   - 识别测风塔数据源（时间跨度<5年）
   - 检查数据文件完整性

2. **配置生成**
   - 设置输入路径为 `parse-sensors` 步骤的输出
   - 配置默认清理规则文件
   - 创建输出目录结构

3. **输出文件**
   - 生成 `process-clean.toml` 配置文件

## 相关文件

- **配置文件**: 待创建配置文档
- **处理命令**: [process clean](../process/clean.md)
- **配置类型**: `src/Types/ProcessCleanConfig.jl`
- **清理规则**: 参考 `formats/clean/default.toml` 文件

## 输出配置示例

```toml
# process-clean.toml
# 基于实际项目结构: projects/pn-3masts/process-clean.toml

[[masts]]
name = "测风塔01"
rules = "formats/clean/default.toml"

    [masts.input]
    data = "./raw/测风塔01.csv"
    sensors = "./raw/测风塔01.sensors.toml"

    [masts.output]
    data = "./clean/测风塔01.csv"
    sensors = "./clean/测风塔01.sensors.yaml"

[[masts]]
name = "测风塔02"
rules = "formats/clean/default.toml"

    [masts.input]
    data = "./raw/测风塔02.csv"
    sensors = "./raw/测风塔02.sensors.toml"

    [masts.output]
    data = "./clean/测风塔02.csv"
    sensors = "./clean/测风塔02.sensors.yaml"
```

## 清理规则文件示例 (formats/clean/default.toml)

```toml
# 风速范围检查
[[rules]]
name = "Wind Speed Range"
sensorType = "WindSpeed"
[rules.out_of_range]
min = 0.0
max = 30.0

# 风向范围检查
[[rules]]
name = "Wind Direction Range"
sensorType = "WindDirection"
[rules.out_of_range]
min = 0.0
max = 360.0

# 风速结冰检测
[[rules]]
name = "Icing WS Detection"
sensorType = "WindSpeed"
[rules.icing]
time_range = 18000    # 5小时 (秒)
max_change = 0.02     # 最大变化量

# 风向结冰检测
[[rules]]
name = "Icing WD Detection"
sensorType = "WindDirection"
[rules.icing]
time_range = 18000
max_change = 1        # 最大变化量 (度)

# 高层风速层差检查
[[rules]]
name = "High Wind Speed Layer Difference"
sensorType = "WindSpeed"
height.min = 70.0     # 适用于70m以上传感器
[rules.layer_difference]
lower_layer_height = 20.0   # 与下方20m处传感器比较
abs_diff.max = 2.0          # 最大绝对差异

# 中层风速层差检查
[[rules]]
name = "Mid Wind Speed Layer Difference"
sensorType = "WindSpeed"
height.max = 50       # 适用于50m以下传感器
[rules.layer_difference]
lower_layer_height = 20.0
abs_diff.max = 3.0    # 更宽松的阈值

# 风向层差检查
[[rules]]
name = "Wind Direction Layer Difference"
sensorType = "WindDirection"
height.min = 70.0
[rules.layer_difference]
lower_layer_height = 20.0
abs_diff.max = 22.5   # 最大角度差异
[rules.layer_difference.lower_wind_speed]
min = 3               # 仅在下层风速3-25m/s时检查
max = 25
```

## 生成的规则类型

### 1. 范围检查规则
- **风速**: 0-80 m/s
- **风向**: 0-360°
- **温度**: -50 到 60°C

### 2. 结冰检测规则
- **检测窗口**: 2小时 (7200秒)
- **变化阈值**: 0.02 m/s (风速), 0.5° (风向)

### 3. 层差检查规则
- **最大层差**: 15 m/s (风速), 45° (风向)
- **检查范围**: 100m 高度差内

### 4. 数据可用性规则
- **最小可用率**: 80%
- **统计窗口**: 1小时 (3600秒)

## 下一步操作

配置生成后，可以执行以下步骤：

1. **检查配置**: 验证生成的配置文件设置
2. **执行清理**: `julia bin/CleanMast.jl process clean ./project/process-clean.toml`
3. **生成下一步配置**: `julia bin/CleanMast.jl recommend tower-shading ./project`

## 注意事项

- 需要先运行 `project parse-sensors` 命令
- 配置文件可以手动编辑以调整清理规则
- 检查输入文件路径是否正确
- 默认规则适用于大多数风能项目，可根据需要调整