# recommend analyze-reconstruct-single

## 概述

生成单测风塔重构分析的配置文件，用于评估重构质量、验证重构效果并生成重构性能报告。

## 语法

```bash
julia bin/CleanMast.jl recommend analyze-reconstruct-single <项目目录>
```

## 实现位置

**核心实现**: `src/AnalyzeReconstructSingle/RecommendAnalyzeReconstructSingleCommand.jl`

## 功能流程

1. **数据对识别**
   - 识别重构前数据（塔影校正后）
   - 识别重构后数据（单测风塔重构后）
   - 验证数据文件的时间对齐

2. **分析配置生成**
   - 配置重构质量评估参数
   - 设置对比分析方法
   - 生成验证和统计配置

3. **输出文件**
   - 生成 `analyze-reconstruct-single.yaml` 配置文件

## 相关文件

- **配置文件**: 待创建配置文档
- **处理命令**: 待创建命令文档
- **配置类型**: `src/Types/AnalyzeReconstructSingleConfig.jl`

## 输出配置示例

```yaml
# analyze-reconstruct-single.yaml
input:
  before_reconstruction:
    data_file: "tower_shading_corrected.csv"
    sensors_file: "sensors.toml"
    label: "塔影校正后数据"

  after_reconstruction:
    data_file: "reconstruct_single.csv"
    sensors_file: "sensors.toml"
    label: "单塔重构后数据"

  reconstruction_logs:
    statistics_file: "reconstruct_single_statistics.json"
    quality_file: "reconstruct_single_quality.csv"

output:
  report_dir: "reports/reconstruct-single"
  formats: ["html", "pdf"]
  language: "zh"

analysis_config:
  validation_methods:
    cross_validation: true        # 交叉验证
    holdout_validation: true      # 留出验证
    bootstrap_validation: true    # 自助法验证

  quality_metrics:
    correlation: true             # 相关系数
    rmse: true                   # 均方根误差
    mae: true                    # 平均绝对误差
    bias: true                   # 偏差
    normalized_metrics: true      # 标准化指标

  statistical_tests:
    normality_test: true         # 正态性检验
    homoscedasticity_test: true  # 同方差性检验
    autocorrelation_test: true   # 自相关检验

  reconstruction_analysis:
    gap_size_analysis: true      # 缺失间隙大小分析
    temporal_patterns: true      # 时间模式分析
    seasonal_performance: true   # 季节性表现分析
    sensor_pair_analysis: true   # 传感器对分析

sensors_config:
  target_sensors:
    - name: "WS_100m_Avg"
      type: "WindSpeed"
      reference_sensors: ["WS_80m_Avg", "WS_60m_Avg"]

    - name: "WS_80m_Avg"
      type: "WindSpeed"
      reference_sensors: ["WS_100m_Avg", "WS_60m_Avg"]

    - name: "WD_100m_Avg"
      type: "WindDirection"
      reference_sensors: ["WD_80m_Avg"]

validation_config:
  artificial_gaps:
    enable: true                 # 启用人工缺失验证
    gap_lengths: [1, 6, 24, 72] # 缺失长度（小时）
    gap_count: 20               # 每种长度的缺失数量
    random_seed: 42             # 随机种子

  test_periods:
    winter: ["2020-12-01", "2021-02-28"]
    spring: ["2021-03-01", "2021-05-31"]
    summer: ["2021-06-01", "2021-08-31"]
    autumn: ["2021-09-01", "2021-11-30"]

reports:
  executive_summary: true        # 执行摘要
  detailed_validation: true     # 详细验证结果
  method_comparison: true       # 方法对比
  sensor_performance: true      # 传感器表现
  recommendations: true         # 改进建议

  charts:
    scatter_plots: true         # 散点图
    residual_plots: true        # 残差图
    time_series_comparison: true # 时间序列对比
    error_distribution: true    # 误差分布
    correlation_matrix: true    # 相关性矩阵
```

## 分析内容详述

### 1. 重构质量评估
- **精度指标**: RMSE, MAE, R², 偏差等统计指标
- **相关性分析**: 重构前后数据的线性和非线性相关性
- **一致性检验**: 重构数据的物理一致性和统计一致性
- **不确定度分析**: 重构结果的置信区间和不确定度

### 2. 方法对比分析
- **多方法评估**: 比较不同重构方法的效果
- **参数敏感性**: 分析关键参数对重构质量的影响
- **适用性评估**: 评估各方法在不同条件下的表现
- **最优策略**: 推荐最适合的重构方法组合

### 3. 时间模式分析
- **季节性表现**: 重构效果的季节变化规律
- **日周期分析**: 重构精度的日内变化特征
- **缺失模式**: 分析数据缺失的时间分布特征
- **长期趋势**: 重构质量的长期变化趋势

### 4. 传感器特异性分析
- **高度依赖性**: 不同高度传感器的重构表现
- **传感器类型**: 风速、风向重构的差异特征
- **相关性要求**: 最小相关性阈值的优化建议
- **参考传感器**: 最佳参考传感器组合推荐

## 验证策略配置

### 1. 交叉验证
- **K折交叉验证**: 数据分为K个子集，轮流作为验证集
- **时间序列交叉验证**: 考虑时间依赖性的验证方法
- **分层交叉验证**: 按风速、季节等分层的验证

### 2. 留出验证
- **随机留出**: 随机选择部分数据作为验证集
- **时间段留出**: 选择特定时间段进行验证
- **条件留出**: 按特定条件（风速、季节）留出数据

### 3. 人工缺失验证
- **控制缺失**: 人为创建缺失数据进行重构测试
- **多尺度缺失**: 测试不同长度缺失的重构效果
- **模式缺失**: 模拟真实的缺失模式进行验证

## 下一步操作

配置生成后，可以执行以下步骤：

1. **检查配置**: 验证分析参数和验证策略
2. **执行分析**: `julia bin/CleanMast.jl analyze reconstruct-single ./project/analyze-reconstruct-single.yaml`
3. **查看报告**: 检查重构质量评估报告
4. **优化重构**: 根据分析结果调整重构参数

## 注意事项

- 需要同时存在重构前后的数据文件
- 验证分析可能需要较长计算时间
- 人工缺失验证会临时修改数据，请确保备份
- 分析结果可用于优化重构配置和方法选择