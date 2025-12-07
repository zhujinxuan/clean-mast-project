# 单测风塔重构算法

## 概述

单测风塔重构算法利用同一测风塔不同高度传感器间的相关性来填补数据缺失。该方法基于大气边界层理论和实际观测的经验关系，是风能数据重构中精度最高、应用最广泛的方法。

## 理论基础

### 大气边界层理论

**对数风廓线定律**
```
U(z) = (u*/k) × ln(z/z₀)

其中：
- U(z): 高度z处的风速
- u*: 摩擦速度
- k: 卡门常数(≈0.4)
- z₀: 粗糙度长度
```

**幂律风廓线**
```
U(z) = U(z_ref) × (z/z_ref)^α

其中：
- U(z_ref): 参考高度风速
- α: 风切变指数
- z_ref: 参考高度
```

**风向随高度变化**
- 埃克曼螺旋效应
- 摩擦力影响随高度减弱
- 地转风向与地面风向差异

### 统计关系建模

**线性回归模型**
```
Y = aX + b + ε

其中：
- Y: 目标高度风速/风向
- X: 参考高度风速/风向
- a, b: 回归参数
- ε: 随机误差项
```

**相关性要求**
- 皮尔逊相关系数 r > 0.8 (风速)
- 圆形相关系数 ρ > 0.7 (风向)

## 风速重构算法

### 1. 简单线性回归
```
算法：风速线性重构
输入：参考高度风速 WS_ref(t), 目标高度 H_target, 参考高度 H_ref
输出：重构的目标高度风速 WS_target(t)

步骤1：数据准备
    提取有效数据对：
    valid_pairs = [(WS_ref(t), WS_target(t)) | 两者均有效]

步骤2：相关性检验
    计算皮尔逊相关系数：
    r = corr(WS_ref_valid, WS_target_valid)

    if r < r_min_threshold:
        返回"相关性不足，无法重构"

步骤3：线性回归拟合
    使用最小二乘法拟合：
    WS_target = a × WS_ref + b

    计算回归参数：
    a = cov(WS_ref, WS_target) / var(WS_ref)
    b = mean(WS_target) - a × mean(WS_ref)

步骤4：质量控制
    计算拟合优度：
    R² = 1 - SS_res/SS_tot
    RMSE = sqrt(mean((WS_target_obs - WS_target_pred)²))

    if R² < R²_min_threshold:
        返回"拟合质量不足"

步骤5：数据重构
    for t in missing_timestamps:
        if WS_ref(t) 有效:
            WS_target(t) = a × WS_ref(t) + b

            # 物理合理性检查
            if WS_target(t) < 0:
                WS_target(t) = 0
            if WS_target(t) > WS_max_physical:
                WS_target(t) = 标记为异常
```

### 2. 分段线性回归
```
算法：风速分段线性重构
输入：参考风速序列, 风速分段点

步骤1：确定分段点
    wind_speed_bins = [0, 3, 8, 15, 25, inf]  # 静风、微风、适中、强风、极强风

步骤2：分段回归建模
    for each bin in wind_speed_bins:
        提取该风速段的数据对
        bin_data = [(WS_ref, WS_target) | WS_ref in bin]

        if len(bin_data) < min_data_points:
            使用相邻分段的参数
        else:
            拟合该分段的线性关系：
            a_bin, b_bin = linear_regression(bin_data)

步骤3：重构应用
    for t in missing_timestamps:
        确定WS_ref(t)所属分段
        bin_index = find_bin(WS_ref(t), wind_speed_bins)

        使用对应分段参数重构：
        WS_target(t) = a_bin[bin_index] × WS_ref(t) + b_bin[bin_index]
```

### 3. 物理约束回归
```
算法：物理约束风速重构
输入：参考风速, 高度信息, 地形参数

步骤1：理论关系约束
    # 基于幂律关系的初始参数估计
    α_theory = estimate_shear_exponent(地形类型, 粗糙度)
    a_initial = (H_target/H_ref)^α_theory

步骤2：约束优化拟合
    定义约束条件：
    - 风切变指数合理范围: 0.05 ≤ α ≤ 0.5
    - 截距接近零: |b| ≤ 0.5 m/s
    - 斜率正值: a > 0

    使用约束最小二乘法：
    minimize: Σ(WS_target_obs - (a×WS_ref + b))²
    subject to: constraints

步骤3：物理一致性验证
    计算隐含风切变指数：
    α_fitted = ln(a) / ln(H_target/H_ref)

    验证是否符合大气物理：
    if α_fitted not in [α_min, α_max]:
        调整约束条件或降级为简单线性回归
```

### 4. 多参考传感器融合
```
算法：多参考传感器融合重构
输入：多个参考高度风速 WS_ref1(t), WS_ref2(t), ...

步骤1：参考传感器评估
    for each ref_sensor:
        计算与目标的相关性: r_i
        计算数据可用性: availability_i
        计算重构质量: quality_i = r_i × availability_i

步骤2：权重分配
    基于质量计算权重：
    w_i = quality_i / Σ(quality_j)

    或基于相关性和距离：
    w_i = r_i² / (1 + |H_target - H_ref_i|/H_scale)

步骤3：融合重构
    for t in missing_timestamps:
        available_refs = [ref_i | WS_ref_i(t) 有效]

        if len(available_refs) == 0:
            无法重构
        elif len(available_refs) == 1:
            使用单一参考重构
        else:
            加权融合重构：
            WS_target(t) = Σ(w_i × WS_target_from_ref_i(t)) / Σ(w_i)

            # 不确定度估计
            uncertainty = sqrt(Σ(w_i × (WS_target_from_ref_i(t) - WS_target(t))²))
```

## 风向重构算法

### 1. 圆形统计回归
```
算法：风向圆形统计重构
输入：参考风向 WD_ref(t), 目标风向观测值（训练）

步骤1：圆形数据预处理
    # 转换为复数表示
    ref_complex = exp(i × WD_ref × π/180)
    target_complex = exp(i × WD_target × π/180)

步骤2：圆形相关性计算
    计算圆形相关系数：
    ρ = |mean(ref_complex × conj(target_complex))|

    if ρ < ρ_min_threshold:
        返回"圆形相关性不足"

步骤3：平均偏移计算
    计算风向偏移：
    offset_complex = mean(target_complex × conj(ref_complex))
    offset_angle = arg(offset_complex) × 180/π

步骤4：重构应用
    for t in missing_timestamps:
        if WD_ref(t) 有效:
            WD_target(t) = WD_ref(t) + offset_angle

            # 标准化到[0, 360)
            WD_target(t) = WD_target(t) mod 360
```

### 2. 风速条件风向重构
```
算法：风速条件风向重构
输入：参考风向, 参考风速, 目标风速

步骤1：风速分层
    根据风速强度分层：
    - 静风: WS < 2 m/s
    - 微风: 2 ≤ WS < 5 m/s
    - 中风: 5 ≤ WS < 10 m/s
    - 强风: WS ≥ 10 m/s

步骤2：分层偏移计算
    for each wind_speed_layer:
        层内数据 = 筛选对应风速范围的风向对

        if 静风层:
            # 静风条件下风向重构不可靠
            标记为不可重构
        else:
            计算该层的平均偏移：
            offset_layer = circular_mean_difference(WD_target_layer, WD_ref_layer)

步骤3：条件重构
    for t in missing_timestamps:
        确定当前风速层：
        layer = classify_wind_speed(WS_ref(t))

        if layer != "静风":
            WD_target(t) = WD_ref(t) + offset_layer
        else:
            标记为无法重构
```

### 3. 风向梯度模型
```
算法：基于物理的风向梯度重构
输入：参考风向, 高度差, 地转参数

步骤1：地转风影响估计
    # 埃克曼层效应
    ekman_depth = 估算埃克曼层深度()
    coriolis_parameter = 2 × Ω × sin(latitude)

步骤2：高度依赖偏移
    理论风向偏移：
    Δθ_theory = f(H_target - H_ref, ekman_depth, coriolis_parameter)

步骤3：经验校正
    基于观测数据校正理论偏移：
    Δθ_empirical = mean(WD_target_obs - WD_ref_obs)
    Δθ_corrected = α × Δθ_theory + (1-α) × Δθ_empirical

    其中α为理论-经验权重因子

步骤4：重构应用
    WD_target(t) = WD_ref(t) + Δθ_corrected
```

## 重构质量评估

### 统计指标
```
算法：重构质量统计评估
输入：重构值序列, 观测值序列（验证集）

计算统计指标：
1. 相关系数 (r):
   r = corr(重构值, 观测值)

2. 均方根误差 (RMSE):
   RMSE = sqrt(mean((重构值 - 观测值)²))

3. 平均绝对误差 (MAE):
   MAE = mean(|重构值 - 观测值|)

4. 偏差 (Bias):
   Bias = mean(重构值 - 观测值)

5. 标准化偏差:
   NBias = Bias / mean(观测值) × 100%

风向特殊指标：
1. 圆形相关系数 (ρ):
   ρ = |mean(exp(i×重构值) × exp(-i×观测值))|

2. 平均绝对圆形误差:
   MACE = mean(min(|重构值-观测值|, 360-|重构值-观测值|))
```

### 物理一致性检验
```
算法：重构物理一致性检验

1. 风切变合理性检验:
   α_reconstructed = ln(WS_target/WS_ref) / ln(H_target/H_ref)

   检验条件：
   - 0.05 ≤ α ≤ 0.5 (一般地形)
   - 日变化合理性
   - 季节变化合理性

2. 能量守恒检验:
   能量密度比 = (0.5×ρ×WS_target³) / (0.5×ρ×WS_ref³)
   理论比值 = (H_target/H_ref)^(3α)

   if |能量密度比 - 理论比值| > tolerance:
       标记为物理不一致

3. 风向梯度检验:
   检验风向随高度变化是否符合大气物理规律
```

### 不确定度量化
```
算法：重构不确定度量化

1. 统计不确定度:
   基于回归残差估计：
   σ_stat = std(residuals)

   考虑样本数量影响：
   σ_corrected = σ_stat × sqrt(1 + 1/n + (x-x̄)²/Sxx)

2. 模型不确定度:
   交叉验证估计：
   for k_fold in cross_validation:
       训练模型，预测验证集
       计算预测误差
   σ_model = std(cv_errors)

3. 总不确定度:
   σ_total = sqrt(σ_stat² + σ_model² + σ_systematic²)

   其中σ_systematic为系统误差估计
```

## 重构策略优化

### 自适应算法选择
```
算法：自适应重构方法选择
输入：数据特征, 质量要求

决策树：
if 相关性 > 0.95 and 数据量 > 2000:
    选择简单线性回归
elif 相关性 > 0.85 and 数据分布不均匀:
    选择分段线性回归
elif 高度差 > 50m:
    选择物理约束回归
elif 多个参考传感器可用:
    选择融合重构
else:
    选择最佳单一参考回归

算法参数自适应调整：
based on 历史重构效果:
    if RMSE > target_accuracy:
        增加约束条件强度
        扩大训练数据窗口
    elif 计算时间 > time_limit:
        简化模型复杂度
        减少数据预处理步骤
```

### 实时重构优化
```
算法：实时重构参数更新
输入：新观测数据, 当前模型参数

滑动窗口更新：
1. 添加新数据点到训练集
2. 移除过旧数据点（超出时间窗口）
3. 重新评估模型参数
4. 更新重构模型

触发条件：
- 新数据数量达到更新阈值
- 重构质量下降超过警戒值
- 季节或环境条件显著变化

参数平滑：
# 避免参数剧烈变化
new_params = α × old_params + (1-α) × fitted_params
其中α为平滑因子
```

## 应用指导

### 算法选择指南

**数据条件与算法匹配**：
```
条件评估矩阵：
                    简单线性  分段回归  物理约束  多传感器融合
相关性 > 0.9         ✓        ✓        ✓         ✓
相关性 0.8-0.9       ×        ✓        ✓         ✓
相关性 0.7-0.8       ×        ×        ✓         ✓
数据量 > 5000       ✓        ✓        ✓         ✓
数据量 1000-5000    ✓        ×        ✓         ✓
数据量 < 1000       ✓        ×        ×         ×
高度差 < 20m        ✓        ✓        ×         ✓
高度差 20-50m       ✓        ✓        ✓         ✓
高度差 > 50m        ×        ✓        ✓         ✓
```

**性能预期**：
- 简单线性回归：RMSE < 0.5 m/s (风速), < 10° (风向)
- 分段线性回归：RMSE < 0.4 m/s (风速), < 8° (风向)
- 物理约束回归：RMSE < 0.6 m/s (风速), < 12° (风向)
- 多传感器融合：RMSE < 0.3 m/s (风速), < 6° (风向)

### 参数推荐值

**通用参数**：
- 最小相关系数阈值：0.8 (风速), 0.7 (风向)
- 最小数据点数：100 (每月), 500 (建模)
- 最大预测区间：±3σ
- 物理约束：风切变指数 0.05-0.5

**环境特定调整**：
- 海上：相关性阈值可适当降低
- 山地：增加物理约束权重
- 城市：考虑更多不确定度
- 森林：调整粗糙度参数

通过系统化的单测风塔重构算法，可以实现高精度的数据填补，为风能资源评估和工程设计提供可靠的数据基础。