# 中尺度数据重构算法

## 概述

中尺度数据重构算法利用数值天气预报模型（如ERA5、MERRA-2等）的再分析数据来填补测风塔观测数据的缺失。该方法通过建立中尺度数据与测风塔观测之间的统计关系，实现长时间序列的数据重构，特别适用于需要长期代表性数据的风能评估项目。

## 理论基础

### 中尺度数据特征

**空间分辨率**
```
典型中尺度数据分辨率：
- ERA5: 0.25° × 0.25° (约28km × 28km)
- MERRA-2: 0.5° × 0.625° (约55km × 69km)
- CFSR: 0.3° × 0.3° (约38km × 38km)
```

**时间分辨率**
```
时间采样频率：
- ERA5: 小时数据
- MERRA-2: 小时数据
- CFSR: 6小时数据
```

**垂直分辨率**
```
大气层高度：
- 地面层: 10m, 50m, 100m
- 低层大气: 200m, 500m, 1000m
- 边界层: 根据模型配置
```

### 尺度差异问题

**空间尺度匹配**
```
问题：中尺度网格 (25-50km) vs 测风塔点观测 (10m)
解决方案：
1. 双线性插值到测风塔位置
2. 地形修正和降尺度
3. 局地效应参数化
```

**时间尺度匹配**
```
问题：中尺度平均场 vs 测风塔瞬时观测
解决方案：
1. 时间插值到测风塔采样频率
2. 亚网格变异性建模
3. 高频成分重构
```

## 中尺度数据预处理

### 1. 空间插值降尺度
```
算法：中尺度数据空间降尺度
输入：中尺度网格数据, 测风塔坐标, 高分辨率地形数据

步骤1：网格点识别
    确定包含测风塔的网格：
    grid_indices = find_grid_cell(mast_lat, mast_lon, grid_coords)

    获取周围4个网格点数据：
    surrounding_grids = get_4_neighbors(grid_indices)

步骤2：双线性插值
    计算插值权重：
    w_ij = distance_weight(mast_position, grid_ij_position)

    双线性插值：
    meso_at_mast = Σ(w_ij × meso_grid_ij)

步骤3：地形修正
    高程修正（假设对数风廓线）：
    WS_corrected = WS_meso × ln(h_mast/z0) / ln(h_meso/z0)

    其中：
    - h_mast: 测风塔高度
    - h_meso: 中尺度模型高度
    - z0: 粗糙度长度

步骤4：粗糙度修正
    基于局地土地利用类型：
    roughness_ratio = z0_local / z0_meso

    粗糙度修正：
    WS_final = WS_corrected × f_roughness(roughness_ratio)
```

### 2. 时间插值和频率匹配
```
算法：中尺度数据时间降尺度
输入：小时/6小时中尺度数据, 目标时间频率

步骤1：时间对齐
    将中尺度数据时间戳对齐到UTC：
    meso_time_utc = convert_timezone(meso_time, 'UTC')

    与测风塔时间戳匹配：
    common_timebase = intersect(meso_time, mast_time)

步骤2：时间插值
    对缺失时间点进行插值：
    if 目标频率 > 中尺度频率:
        # 线性插值到更高频率
        interp_data = linear_interpolate(meso_data, target_timebase)

        # 添加高频变异性
        high_freq_noise = generate_realistic_noise(interp_data)
        final_data = interp_data + high_freq_noise

步骤3：周期性保持
    保持日循环和季节循环特征：
    diurnal_cycle = extract_diurnal_pattern(meso_data)
    seasonal_cycle = extract_seasonal_pattern(meso_data)

    应用周期性模式：
    enhanced_data = apply_cycles(interp_data, diurnal_cycle, seasonal_cycle)

步骤4：统计特性匹配
    匹配高阶统计量：
    target_std = match_standard_deviation(enhanced_data, reference_std)
    target_skew = match_skewness(target_std, reference_skew)
```

### 3. 多变量数据整合
```
算法：多变量中尺度数据整合
输入：风速、风向、温度、气压等多变量数据

步骤1：变量一致性检查
    检查物理一致性：
    # 地转风关系检查
    geostrophic_balance = check_geostrophic(u_wind, v_wind, pressure_gradient)

    # 热力学一致性
    thermal_balance = check_thermal(temperature, pressure, humidity)

步骤2：变量间相关性建模
    计算变量间相关结构：
    correlation_matrix = compute_correlation(wind_speed, wind_dir, temperature, pressure)

    建立多变量模型：
    multivariate_model = fit_copula(correlation_matrix)

步骤3：协同降尺度
    利用变量间关系改善降尺度：
    # 温度梯度信息改善风速估计
    enhanced_wind = wind_base + α × temperature_gradient

    # 气压梯度信息改善风向估计
    enhanced_dir = wind_dir_base + β × pressure_gradient_direction

步骤4：物理约束应用
    应用物理定律约束：
    # 能量守恒
    total_energy = kinetic_energy + potential_energy = constant

    # 动量守恒
    momentum_flux = ρ × u × v = conserved
```

## 统计关系建模

### 1. 线性回归建模
```
算法：中尺度-测风塔线性关系建模
输入：同期中尺度数据和测风塔观测数据

步骤1：数据准备
    提取重叠时间段：
    overlap_period = intersect(meso_dates, mast_dates)

    数据质量控制：
    valid_pairs = filter_valid_data(meso_data, mast_data)

步骤2：相关性分析
    计算线性相关系数：
    r = correlation(meso_wind, mast_wind)

    if r < min_correlation_threshold:
        return "相关性不足，建议使用其他方法"

步骤3：回归建模
    简单线性回归：
    mast_wind = a × meso_wind + b + ε

    参数估计：
    a = cov(meso_wind, mast_wind) / var(meso_wind)
    b = mean(mast_wind) - a × mean(meso_wind)

步骤4：模型诊断
    计算拟合统计量：
    R² = 1 - SS_residual / SS_total
    RMSE = sqrt(mean(residuals²))
    Bias = mean(residuals)

    残差分析：
    plot_residuals_vs_fitted()
    check_residual_normality()
    check_residual_autocorrelation()

步骤5：模型验证
    交叉验证：
    for k_fold in cross_validation:
        train_subset, test_subset = split_data(k_fold)
        model_k = fit_regression(train_subset)
        error_k = predict_and_evaluate(model_k, test_subset)

    validation_RMSE = mean(cross_validation_errors)
```

### 2. 非线性回归建模
```
算法：非线性中尺度-测风塔关系建模
输入：中尺度数据, 测风塔数据, 环境变量

步骤1：非线性关系探索
    散点图分析：
    plot(meso_wind, mast_wind)

    识别非线性模式：
    - 阈值效应（低风速饱和）
    - 上限效应（高风速截断）
    - 季节性变化（不同斜率）

步骤2：分段回归建模
    确定分段点：
    breakpoints = find_breakpoints(meso_wind, mast_wind)

    分段线性拟合：
    for each segment:
        segment_data = data[breakpoint[i]:breakpoint[i+1]]
        a_i, b_i = linear_fit(segment_data)

步骤3：平滑非线性拟合
    样条回归：
    spline_model = fit_smoothing_spline(meso_wind, mast_wind, smoothing_param)

    或多项式回归：
    polynomial_model = fit_polynomial(meso_wind, mast_wind, degree=3)

步骤4：模型选择
    AIC模型选择：
    AIC = n × ln(MSE) + 2k

    其中：
    - n: 样本数量
    - MSE: 均方误差
    - k: 参数数量

    选择AIC最小的模型

步骤5：非线性预测
    应用最优模型进行预测：
    mast_predicted = optimal_model.predict(meso_new)

    不确定度传播：
    prediction_intervals = compute_prediction_intervals(optimal_model, meso_new)
```

### 3. 机器学习建模
```
算法：机器学习中尺度重构建模
输入：多维中尺度特征, 测风塔目标变量

步骤1：特征工程
    基础特征：
    features_basic = [wind_speed, wind_direction, temperature, pressure]

    衍生特征：
    features_derived = [
        wind_speed_squared,           # 非线性项
        wind_speed × temperature,     # 交互项
        rolling_mean(wind_speed, 24), # 时间滞后
        gradient(pressure),           # 空间梯度
        season_indicator,             # 季节指示
        hour_of_day                   # 时间指示
    ]

    特征标准化：
    features_normalized = (features - mean) / std

步骤2：模型训练
    随机森林：
    rf_model = RandomForest(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5
    )

    神经网络：
    nn_model = NeuralNetwork(
        hidden_layers=[64, 32, 16],
        activation='relu',
        dropout=0.2
    )

    梯度提升：
    gbm_model = GradientBoosting(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=6
    )

步骤3：超参数优化
    网格搜索：
    param_grid = {
        'n_estimators': [50, 100, 200],
        'max_depth': [5, 10, 15],
        'learning_rate': [0.01, 0.1, 0.2]
    }

    交叉验证网格搜索：
    best_params = grid_search_cv(model, param_grid, cv=5)

步骤4：模型集成
    集成多个模型：
    ensemble_prediction = w1×rf_pred + w2×nn_pred + w3×gbm_pred

    权重优化：
    weights = optimize_ensemble_weights(models, validation_data)

步骤5：特征重要性分析
    分析特征对预测的贡献：
    feature_importance = model.feature_importances_

    SHAP值分析：
    shap_values = compute_shap_values(model, features)
```

## 长期重构与代表年校准

### 1. 长期数据重构
```
算法：基于中尺度数据的长期重构
输入：短期测风塔数据, 长期中尺度数据, 训练好的转换模型

步骤1：重构策略
    确定重构目标：
    - 目标年份范围（如1980-2020）
    - 目标时间分辨率（如10分钟）
    - 目标参数（风速、风向、温度等）

步骤2：模型应用
    批量应用训练模型：
    for year in target_years:
        meso_year_data = load_meso_data(year)
        mast_year_reconstructed = model.predict(meso_year_data)

        # 质量控制
        qc_data = quality_control(mast_year_reconstructed)

步骤3：时间一致性检查
    检查长期趋势一致性：
    meso_trend = calculate_trend(meso_long_term)
    reconstructed_trend = calculate_trend(reconstructed_long_term)

    if |meso_trend - reconstructed_trend| > threshold:
        apply_trend_correction()

步骤4：统计特性保持
    保持观测期统计特性：
    # 均值保持
    adjust_mean(reconstructed_data, observed_mean)

    # 方差保持
    adjust_variance(reconstructed_data, observed_variance)

    # 极值分布保持
    adjust_extremes(reconstructed_data, observed_extremes)

步骤5：不确定度量化
    传播重构不确定度：
    model_uncertainty = estimate_model_uncertainty()
    reconstruction_uncertainty = propagate_uncertainty(model_uncertainty, input_data)

    置信区间：
    CI_lower = reconstructed_value - 1.96 × reconstruction_uncertainty
    CI_upper = reconstructed_value + 1.96 × reconstruction_uncertainty
```

### 2. 代表年校准
```
算法：代表年识别与校准
输入：长期重构数据, 观测数据

步骤1：代表性评估指标
    风能密度指标：
    WPD_annual = mean(0.5 × ρ × WS³) for each year

    风速分布指标：
    weibull_params = fit_weibull(WS_annual) for each year
    shape_parameter, scale_parameter = weibull_params

    极值指标：
    extreme_wind = annual_maximum(WS) for each year

步骤2：代表年筛选
    多指标综合评估：
    representativeness_score = w1×WPD_score + w2×distribution_score + w3×extreme_score

    where:
    WPD_score = 1 - |WPD_year - WPD_longterm| / WPD_longterm
    distribution_score = correlation(monthly_WPD_year, monthly_WPD_longterm)
    extreme_score = 1 - |extreme_year - extreme_longterm| / extreme_longterm

    候选代表年：
    representative_years = top_N_years(representativeness_score)

步骤3：代表年验证
    与观测期对比验证：
    for candidate_year in representative_years:
        validation_metrics = compare_with_observations(candidate_year, obs_period)

        # 月度变化一致性
        monthly_correlation = corr(monthly_pattern_year, monthly_pattern_obs)

        # 日变化一致性
        diurnal_correlation = corr(diurnal_pattern_year, diurnal_pattern_obs)

        # 风向分布一致性
        wind_rose_similarity = compare_wind_roses(year_data, obs_data)

步骤4：校准修正
    如需要，对代表年进行微调：
    # 偏差修正
    bias_correction = mean(obs_data) - mean(representative_year_data)
    corrected_data = representative_year_data + bias_correction

    # 方差修正
    variance_correction = std(obs_data) / std(representative_year_data)
    final_data = corrected_data × variance_correction

步骤5：不确定度评估
    代表性不确定度：
    inter_annual_variability = std(annual_WPD_all_years)
    representativeness_uncertainty = inter_annual_variability / sqrt(n_years)

    总不确定度：
    total_uncertainty = sqrt(model_uncertainty² + representativeness_uncertainty²)
```

## 质量控制与验证

### 重构数据质量评估
```
算法：中尺度重构质量评估

1. 统计一致性检验：
   # 基本统计量对比
   mean_bias = mean(reconstructed) - mean(observed)
   variance_ratio = var(reconstructed) / var(observed)
   correlation = corr(reconstructed, observed)

2. 分布一致性检验：
   # Kolmogorov-Smirnov检验
   ks_statistic, p_value = ks_test(reconstructed, observed)

   # 韦伯分布参数对比
   weibull_params_recon = fit_weibull(reconstructed)
   weibull_params_obs = fit_weibull(observed)

3. 时间序列特性检验：
   # 自相关结构
   autocorr_recon = compute_autocorrelation(reconstructed)
   autocorr_obs = compute_autocorrelation(observed)

   # 频谱特性
   psd_recon = power_spectral_density(reconstructed)
   psd_obs = power_spectral_density(observed)

4. 极值特性检验：
   # 年最大值分布
   annual_maxima_recon = extract_annual_maxima(reconstructed)
   annual_maxima_obs = extract_annual_maxima(observed)

   # 超阈值分布
   threshold = percentile(observed, 95)
   peaks_over_threshold_comparison(reconstructed, observed, threshold)
```

## 应用指导

### 算法选择策略
```
选择决策树：

if 观测期 < 6个月:
    建议延长观测期或使用其他方法

elif 观测期 6个月-1年:
    使用简单线性回归 + 季节调整

elif 观测期 1-2年:
    使用非线性回归或浅层机器学习

elif 观测期 > 2年:
    使用深度学习或复杂集成模型

地形条件考虑：
if 地形复杂度高:
    增加地形特征和降尺度修正

if 海上或简单地形:
    可使用相对简单的模型
```

### 参数推荐值
```
通用参数：
- 最小观测期：6个月（包含完整季节变化）
- 最小相关系数：0.7（风速），0.6（风向）
- 交叉验证折数：5-10折
- 特征选择阈值：重要性 > 0.01

质量控制阈值：
- 均值偏差：< ±10%
- 方差比：0.8-1.2
- 相关系数：> 0.8
- KS检验p值：> 0.05

不确定度量化：
- 95%置信区间
- 模型不确定度 + 数据不确定度
- 长期变异性考虑
```

通过系统化的中尺度数据重构算法，可以实现长期、连续的风能数据序列重构，为风能资源长期评估和风电场设计提供可靠的数据基础。