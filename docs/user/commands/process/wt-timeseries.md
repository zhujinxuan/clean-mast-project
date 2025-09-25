# process wt-timeseries

## 概述

导出Meteodyn格式的风机轮毂高度时间序列数据，专注于120m以上高度或最高两层，为风机性能分析和发电量计算提供标准化输入。

## 语法

```bash
julia bin/CleanMast.jl process wt-timeseries <配置文件路径>
```

## 前置条件

- 必须先完成 `process representative-year` 步骤
- 存在 `wt-timeseries.toml` 配置文件

## 配置文件格式 (TOML)

### 基本结构

```toml
[[masts]]
name = "测风塔名称"
output_dir = "输出目录"
target_heights = [高度1, 高度2, ...]
    [masts.input]
    sensors = "输入传感器配置文件"
    data = "输入数据文件"
```

### 配置参数

#### 测风塔配置 (`masts`)
- **name**: 测风塔唯一标识符
- **output_dir**: 时间序列文件输出目录
- **target_heights**: 目标导出高度列表 (米，自动选择120m以上或最高两层)
- **input.sensors**: 输入传感器元数据文件 (来自 representative-year)
- **input.data**: 输入时间序列数据文件 (来自 representative-year)

### 完整配置示例

```toml
[[masts]]
name = "测风塔-001"
output_dir = "wt-timeseries"
target_heights = [120.0]  # 仅120m (唯一符合条件的高度)
    [masts.input]
    sensors = "./representative-year/测风塔-001.sensors.yaml"
    data = "./representative-year/测风塔-001.csv"

[[masts]]
name = "测风塔-002"
output_dir = "wt-timeseries"
target_heights = [120.0, 140.0]  # 最高两层 (均≥120m)
    [masts.input]
    sensors = "./representative-year/测风塔-002.sensors.yaml"
    data = "./representative-year/测风塔-002.csv"

[[masts]]
name = "测风塔-003"
output_dir = "wt-timeseries"
target_heights = [140.0, 160.0]  # 最高两层 (有更低于120m的层时只取最高两层)
    [masts.input]
    sensors = "./representative-year/测风塔-003.sensors.yaml"
    data = "./representative-year/测风塔-003.csv"
```

## 输入文件

- **代表年数据**: 来自 representative-year 步骤的传感器配置和时间序列数据
- **传感器配置**: `.yaml` 格式，包含各高度层传感器信息

## 输出文件

输出Meteodyn兼容格式的时间序列文件：

- `wt-timeseries/<测风塔名称>_<高度>m.csv`: 各高度层时间序列数据
- `wt-timeseries/<测风塔名称>_summary.yaml`: 导出统计信息

### 输出格式说明

每个高度层的CSV文件包含以下列：
- **timestamp**: 时间戳 (ISO 8601格式)
- **wind_speed**: 风速 (m/s)
- **wind_direction**: 风向 (°)
- **temperature**: 温度 (°C，如可用)
- **pressure**: 气压 (hPa，如可用)

## 高度选择策略

系统自动选择合适的导出高度：

- **优先条件**: 所有120m及以上的测量高度
- **备选策略**: 如果120m以上高度不足，则选择最高的两个测量高度
- **风机相关**: 120m是常见的风机轮毂高度下限
- **性能优化**: 集中于最相关的高度层，减少不必要的数据量

## 高度插值方法

当目标高度与实测高度不匹配时，系统自动进行插值：

- **垂直插值**: 基于邻近传感器数据进行线性或对数插值
- **风切变校正**: 考虑大气稳定度的风切变模型
- **方向一致性**: 确保不同高度间风向的物理合理性

## 配置生成

使用 `recommend` 命令生成配置文件：

```bash
julia bin/CleanMast.jl recommend wt-timeseries projects/my-windfarm
```

## 使用场景

导出的时间序列数据可用于：

1. **Meteodyn WT**: 风机微观选址和尾流分析
2. **发电量评估**: AEP (Annual Energy Production) 计算
3. **风机性能分析**: 功率曲线验证和优化
4. **载荷分析**: 疲劳载荷和极端载荷评估