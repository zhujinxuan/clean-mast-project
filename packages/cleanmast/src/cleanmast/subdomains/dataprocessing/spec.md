## Code rules

### Purpose
Data processing domain services: reconstruction, height filling, turbulence
calculation, WT timeseries generation. All computation; no I/O of any kind.

### Rules
- Inherits all rules from `subdomains/spec.md`.
- **No I/O of any kind.** Never import `TimeSeriesSource`, `TimeSeriesRepository`,
  or any I/O symbol. Input: `TimeSeriesData` or `numpy` arrays only.
  (Constructing config IR that carries `TimeSeriesSource` paths — e.g.
  `MastFillConfig.input` / `.output` — is allowed; loading through them is not.)
- Strategy objects (`strategies/`) conform to a structural protocol:
  no base class coupling.
- Fitting functions (`fitting.py`) are pure numpy math over
  extracted Series/arrays; no polars DataFrame manipulation inside fit
  functions.
- Public API: services are callable module-level functions; the
  `__init__.py` under `services/` exports all public symbols.

### Anti-patterns
- Importing `cleanmast.subdomains.configuration` (enforced:
  `repository-access` contract).
- Loading config files inside compute — all config I/O belongs in the
  application usecase.
- Stateful calculators; prefer pure functions with explicit inputs.

### When in doubt
- If a function needs data + config → split: load in the usecase, compute
  in dataprocessing.
- If two strategies share logic → extract to `helpers.py` or `fitting.py`.

## 业务说明 (Business description)

### Domain context

dataprocessing 是风资源评估管道的计算引擎: 重建(单塔/交叉/中尺度)
中的缺失数据、将已知高度数据推算至目标轮毂高度(fill-heights)、
生成风机位置的时序数据(wt-timeseries)、计算湍流强度。

### Key concepts

**Fill-heights (高度补全):** 利用风切变模型，从已知高度传感器的实测数据
推算目标高度的风速和风向。核心物理假设: 风切变遵循幂律
(power law) v₂/v₁ = (h₂/h₁)^α，风向随高度线性变化。

**remove-top-layer 策略:** 训练时移除最高层传感器的实测数据作为
"真实值" (ground truth)，用剩余传感器拟合模型参数，再与移除的真实值
对比评估拟合质量。这是当前唯一的训练策略；未来可扩展
`per-timestamp-extrapolation` 等策略。

**风切变指数 (shear, α):** 幂律指数，描述风速随高度的增长速率。
从 top-3 高层传感器拟合 (近地面受粗糙度影响，低层传感器代表性差)。
α 是站点的物理属性，与数据源无关 — 从 reconstruct-meso 拟合的 α
可直接用于 representative-year 补全。

**风向变化率 (deg_diff_per_m):** 风向随高度的旋转速率 (deg/m)，
由 Ekman 螺旋效应产生。从 top-3 风向传感器拟合。
限制阈值 1.125 deg/m (22.5° / 20 m) 过滤不合理的拟合值。

**高度补全策略:** 区分外推 (extrapolation: 目标高度高于最高传感器)
和内插 (interpolation: 目标高度在已有传感器之间)。
外推使用 top-3 拟合参数；内插使用邻近两个传感器的局部拟合。

**Wind turbine timeseries (风机时序):** 从补全后的测风塔数据生成
每个风机位置的时序 — 包括轮毂高度风速/风向、湍流强度。

### Business constraints

- 补全精度直接影响风功率估算: 1% 的风速误差 ≈ 3% 的功率误差
  (P ∝ v³)。
- top-3 拟合是最小化近地面粗糙度干扰的工程惯例。
- 外推的物理有效性限制: 幂律在边界层内成立 (通常 ≤ 200 m)，
  补全高度不应显著超出最高传感器的高度范围。
- 截面风廓线和方向变化假设风速/风向仅随高度变化，忽略水平不均匀性。
