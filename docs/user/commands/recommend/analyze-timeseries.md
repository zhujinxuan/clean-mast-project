# recommend analyze-timeseries

## 概述

生成时间序列分析的配置文件，用于综合分析风能资源特征和生成详细的统计报告。

## 语法

```bash
julia bin/CleanMast.jl recommend analyze-timeseries <项目目录>
```

## 实现位置

**核心实现**: `src/AnalyzeTimeSeries/RecommendAnalyzeTimeSeriesCommand.jl`

## 功能流程

1. **数据源识别**
   - 扫描项目目录，识别最终处理的数据文件
   - 检测数据处理链的完成状态
   - 选择最高质量的数据源

2. **分析配置生成**
   - 配置综合分析参数
   - 设置报告输出路径和格式
   - 选择适当的分析方法

3. **输出文件**
   - 生成 `analyze-timeseries.yaml` 配置文件

## 相关文件

- **配置文件**: 待创建配置文档
- **处理命令**: 待创建命令文档
- **配置类型**: `src/Types/AnalyzeTimeSeriesConfig.jl`

## 输出配置示例

```toml
# analyze-rep.toml (代表年分析配置)
# 基于实际项目结构: projects/pn-3masts/analyze-rep.toml
# 分析代表年校准结果的综合配置

[[masts]]
name = "pn-002824"
[masts.input]
data = "./representative-year/pn-002824.csv"
sensors = "./representative-year/pn-002824.sensors.yaml"
[masts.airDensity]
density = 1.225  # kg/m³ at sea level, 15°C
reference_height = 10.0

[[masts]]
name = "pn-013945"
[masts.input]
data = "./representative-year/pn-013945.csv"
sensors = "./representative-year/pn-013945.sensors.yaml"
[masts.airDensity]
density = 1.225  # kg/m³ at sea level, 15°C
reference_height = 10.0

[[masts]]
name = "pn-014576"
[masts.input]
data = "./representative-year/pn-014576.csv"
sensors = "./representative-year/pn-014576.sensors.yaml"
[masts.airDensity]
density = 1.225  # kg/m³ at sea level, 15°C
reference_height = 10.0

[output]
path = "./analyze-representative-year"
```

**注意**: 实际项目中使用的是 `analyze-rep.toml` 用于代表年分析，这是时间序列分析的一种特殊形式，专注于代表年校准后的数据质量评估。

## 分析内容配置

### 1. 风资源分析
- **风速分布**: 韦伯分布拟合，形状和尺度参数
- **风向分布**: 16扇区风玫瑰图，主导风向分析
- **风能密度**: 不同高度的风能密度计算
- **切变分析**: 风速随高度变化规律

### 2. 时间特征分析
- **日变化**: 24小时风速风向变化模式
- **季节变化**: 春夏秋冬风资源差异
- **年际变化**: 多年数据的年际波动
- **极值分析**: 极大风速的统计特征

### 3. 工程参数计算
- **年平均风速**: 不同高度的年平均风速
- **风能密度**: 单位面积风能通量
- **湍流强度**: 各风速区间的湍流特征
- **风切变指数**: 大气稳定度相关参数

### 4. 发电量评估
- **理论发电量**: 基于风机功率曲线
- **容量因子**: 年度平均容量因子
- **发电小时数**: 等效满发小时数
- **发电量分布**: 月度和季节发电量变化

## 自动配置优化

该命令会自动：

1. **数据适配分析**
   - 检测可用的传感器类型和高度
   - 评估数据质量和完整性
   - 选择最适合的分析参数

2. **报告定制**
   - 根据数据特征调整分析内容
   - 选择合适的图表类型
   - 配置报告语言和格式

3. **性能优化**
   - 估算分析所需的计算时间
   - 配置合适的时间聚合级别
   - 优化内存使用策略

## 下一步操作

配置生成后，可以执行以下步骤：

1. **检查配置**: 验证分析参数和报告设置
2. **执行分析**: `julia bin/CleanMast.jl analyze timeseries ./project/analyze-timeseries.yaml`
3. **查看报告**: 检查生成的HTML/PDF报告
4. **结果解读**: 分析风资源特征和工程参数

## 注意事项

- 建议使用完整处理链的最终数据
- 长期数据分析可能需要较长计算时间
- 报告生成需要足够的磁盘空间
- 可根据具体需求调整分析参数和报告内容