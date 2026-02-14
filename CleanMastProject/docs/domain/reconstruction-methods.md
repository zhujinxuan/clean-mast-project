# 重构方法选择指南

> **本文档类型**: 领域知识文档（需专家审核）
> 
> **审核标记**: `:llm-domain-write:`

## 概述

CleanMast 提供四种数据重构方法，分别适用于不同的数据缺失场景和数据条件。本指南帮助用户根据实际情况选择最合适的重构策略。

**核心原则**：优先使用精度更高的方法，精度相当的情况下优先使用计算成本更低的方法。

| 重构方法 | 精度 | 计算成本 | 适用场景 |
|----------|------|----------|----------|
| 单测风塔重构 | 高 | 低 | 单塔垂直相关性填补 |
| 跨测风塔重构 | 中高 | 中 | 多塔空间相关性填补 |
| 中尺度重构 | 中 | 中 | 长期缺失填补 |
| 代表年校准 | 中 | 高 | 长期气候代表性校准 |

## 方法对比速览

### 单测风塔重构

**原理**：利用同一测风塔不同高度传感器之间的垂直相关性进行数据填补。

**优点**：
- 精度最高（塔上传感器相关性最强）
- 计算成本最低
- 不需要外部数据源

**缺点**：
- 要求塔上至少有三个高度层传感器
- 仅适用于短期、小范围缺失

**适用条件**：
- 目标高度存在有效参考传感器
- 参考高度与目标高度数据相关性满足要求
- 缺失时段存在有效参考数据

### 跨测风塔重构

**原理**：利用项目区域内多测风塔之间的空间相关性进行数据填补。

**优点**：
- 利用塔间相似风况条件
- 可填补单塔无法完成的长期缺失

**缺点**：
- 需要多塔数据
- 塔间距离影响重构质量

**适用条件**：
- 项目区域内有多个测风塔（建议三座及以上）
- 塔间距离在合理范围内
- 各塔有重叠观测时段

### 中尺度重构

**原理**：利用中尺度再分析数据（ERA5、MERRA-2等）通过训练模型转换为测风塔等效数据。

**优点**：
- 可填补任意时长的数据缺失
- 不依赖其他测风塔数据

**缺点**：
- 精度低于塔上重构方法
- 需要前期训练模型

**适用条件**：
- 存在连续数周以上的长期缺失
- 有可用的中尺度再分析数据
- 已完成中尺度模型训练

### 代表年校准

**原理**：将短期观测数据校准为反映长期气候特征的代表性数据。

**优点**：
- 提供长期气候代表性数据
- 支持风能资源长期评估

**缺点**：
- 计算成本最高
- 需要完整的长期中尺度数据

**适用条件**：
- 需要长期风能资源评估
- 观测期与长期气候存在偏差
- 已完成中尺度模型训练

## 决策流程图

```
开始分析数据缺失情况
        │
        ▼
┌───────────────────────┐
│ 单塔是否有≥3个高度层？ │
└─────────┬─────────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
   是          否
    │           │
    ▼           ▼
┌───────┐   ┌───────────────────┐
│垂直相关性│   │ 是否有多座相邻测风塔？│
│能否建立？│   └───────┬─────────┘
└───┬───┘           │
    │         ┌─────┴─────┐
    │         ▼           ▼
    │        是          否
    │         │           │
    ▼         ▼           ▼
┌───────┐ ┌───────┐ ┌───────────────────┐
│单塔重构│ │跨塔重构│ │ 是否有中尺度数据？ │
└───┬───┘ └───┬───┘ └───────┬─────────┘
    │         │           │
    ▼         │           │
┌───────┐     │     ┌─────┴─────┐
│  完成 │     │     ▼           ▼
└───────┘     │    是          否
              │     │           │
              ▼     ▼           ▼
        ┌───────────┐   ┌───────────┐
        │ 跨塔+中尺度│   │ 无法重构  │
        │   联合使用 │   │ 记录缺失  │
        └─────┬─────┘   └───────────┘
              │
              ▼
        ┌───────────┐
        │是否需要长期│
        │气候代表性？│
        └─────┬─────┘
              │
        ┌─────┴─────┐
        ▼           ▼
       是          否
        │           │
        ▼           ▼
┌───────────────┐ ┌───────────┐
│ 代表年校准     │ │   完成    │
└───────────────┘ └───────────┘
```

## 各方法详细说明

### 单测风塔重构

**适用场景**：

1. 单个高度层传感器短时间缺失的数据填补
2. 多高度层测风数据的相互验证和补充
3. 塔影校正后缺失值的后续重建
4. 数据清理阶段标记为可恢复的异常值填补

**数据要求**：

| 要求项 | 详细说明 |
|--------|----------|
| 最低高度阈值 | 50m 以上传感器（可配置） |
| 最小数据可用率 | 该小时内有效数据比例 ≥ 50% |
| 最少合格层数 | 不足 3 层则跳过该小时 |
| 重构成功条件 | 参考层与目标高度相关性满足要求 |

**命令执行**：

```bash
# 推荐配置生成
julia bin/CleanMast.jl recommend reconstruct-single

# 执行重构
julia bin/CleanMast.jl process reconstruct-single --config reconstruct-single.toml
```

**配置示例**：

```toml
[[masts]]
name = "pn-002824"

[masts.input]
data = "./tower-shading/pn-002824.csv"
sensors = "./tower-shading/pn-002824.sensors.yaml"

[masts.output]
data = "./reconstruct-single/pn-002824.csv"
sensors = "./reconstruct-single/pn-002824.sensors.yaml"
```

**使用建议**：

- 测风塔高度层越多（建议 ≥ 4 层），重构成功率越高
- 若某小时数据缺失较多但仍有一定参考价值，可降低可用率阈值至 0.3-0.4

### 跨测风塔重构

**适用场景**：

1. 多塔项目：项目区域内有多个测风塔
2. 数据不均衡：部分塔数据完整度高，部分塔存在较多缺失
3. 塔间距离适中：测风塔间距在合理范围内
4. 同期观测：各塔有重叠的时间段可用于训练分析

**数据要求**：

| 要求项 | 详细说明 |
|--------|----------|
| 最小重叠天数 | 120天（确保足够的季节性覆盖） |
| 最小相关系数 | 风速 ≥ 0.7，风向 ≥ 0.5 |
| 风向标准差阈值 | 12.5° |
| 有效数据点 | 每对塔至少 100 个并发数据点 |

**命令执行**：

```bash
# 训练阶段
julia bin/CleanMast.jl process train-reconstruct-cross --config train-reconstruct-cross.toml

# 重构阶段
julia bin/CleanMast.jl process reconstruct-cross --config reconstruct-cross.toml
```

**配置示例**：

```toml
# 训练配置
[[masts]]
name = "TGL1"
input = { data = "./clean/TGL1.parquet", sensors = "./clean/TGL1.sensors.toml" }

[[masts]]
name = "TGL2"
input = { data = "./clean/TGL2.parquet", sensors = "./clean/TGL2.sensors.toml" }

[train]
min_overlap_days = 120
min_correlation_speed = 0.7
min_correlation_direction = 0.5
max_direction_std = 12.5
output_dir = "./cross-mast-models"

# 重构配置
[[reconstructions]]
target_mast = "TGL1"
source_masts = ["TGL2", "TGL3"]
priority = 1

[reconstructions.model]
model_file = "./cross-mast-models/TGL1_TGL2.jld2"
```

**使用建议**：

- 优先使用高相关性塔对进行重构
- 建议将重构结果与原始数据进行对比验证

### 中尺度重构

**适用场景**：

1. 数据缺口较大：测风塔存在连续数周甚至数月的长期数据缺失
2. 长期代表性评估：需要进行 20-30 年的长期风能资源评估
3. 多年度对比分析：需要比较不同年份的风能特征
4. 与历史工程数据衔接：需要与多年前的历史测风数据进行对比

**数据要求**：

| 要求项 | 详细说明 |
|--------|----------|
| 训练数据 | 测风塔完整观测期数据（建议 ≥ 6 个月） |
| 中尺度数据 | 同期中尺度再分析数据（ERA5、MERRA-2 等） |
| 训练模型 | 已保存的中尺度转换模型文件 |
| 时间对齐 | 测风塔与中尺度数据时间戳完全一致 |

**命令执行**：

```bash
# 训练阶段
julia bin/CleanMast.jl process train-meso --config train-meso.toml

# 重构阶段
julia bin/CleanMast.jl process reconstruct-meso --config reconstruct-meso.toml
```

**配置示例**：

```toml
# reconstruct-meso.toml
[[masts]]
name = "PN01"

[masts.input]
type = "csv"
path = "projects/pn-masts/outputs/cleaned/PN01_cleaned_10min.parquet"

[masts.output]
type = "parquet"
path = "projects/pn-masts/outputs/reconstructed_meso/PN01_reconstructed_meso.parquet"

[masts.time_range]
start = "2020-01-01T00:00:00"
end = "2023-12-31T23:50:00"

[masts.models.windspeed]
method = "SectorizedRegression"
meso_name = "ERA5"
model_file = "models/PN01_windspeed_era5_model.jls"

[masts.models.winddirection]
method = "DirectionOffset"
meso_name = "ERA5"
model_file = "models/PN01_winddirection_era5_model.jls"

[[mesos]]
name = "ERA5"
type = "csv"
path = "data/era5/era5_pn_region_2020_2023.csv"
```

**使用建议**：

- ERA5 通常在陆地区域表现较好
- 选择适合项目区域的中尺度数据源很重要
- 建议使用 8-12 个风向扇区，对复杂地形风向效应更鲁棒

### 代表年校准

**适用场景**：

1. 长期风能资源评估：需要评估风电场的长期发电潜力
2. 风电场设计参数确定：需要基于长期极端风速、湍流强度等参数
3. 年发电量估算：使用代表年数据进行年发电量估算
4. 不同风电场数据对比：对比不同地点或不同时间段的发电性能

**数据要求**：

| 要求项 | 详细说明 |
|--------|----------|
| 训练期 | 建议 ≥ 6 个月，确保季节性覆盖 |
| 气候学期 | 最多 30 年完整年度数据 |
| 校准阈值 | 训练期与完整期平均差异超过 2% 才校准 |
| 代表年阈值 | 候选年与气候学平均最大允许差异 2% |

**命令执行**：

```bash
# 生成配置
julia bin/CleanMast.jl recommend representative-year

# 执行校准
julia bin/CleanMast.jl process representative-year --config representative-year.toml
```

**配置示例**：

```toml
[[masts]]
name = "TGL1"
input = { data = "./reconstruct-meso/TGL1.parquet" }
output = { data = "./representative-year/TGL1.parquet" }
time_range = { min = "2023-01-01T00:00:00", max = "2023-12-31T23:50:00" }

[masts.meso_model]
method = "16-sector"
meso_name = "era5"
model_file = "./meso-models/TGL1-era5.jld2"

[[mesos]]
name = "era5"
data = "./raw/era5.parquet"
sensors = "./raw/era5.sensors.toml"
```

**使用建议**：

- 校准结果自动限制在物理合理范围内：[0.5, 25.0] m/s
- 如果训练期与长期气候差异不超过 2%，自动跳过校准

## 联合使用策略

### 推荐执行顺序

| 顺序 | 方法 | 何时使用 | 命令 |
|------|------|----------|------|
| 1 | 单测风塔重构 | 首先处理短期缺失 | `process reconstruct-single` |
| 2 | 跨测风塔重构 | 单塔无法处理时 | `process reconstruct-cross` |
| 3 | 中尺度重构 | 长期缺失无法通过跨塔处理 | `process reconstruct-meso` |
| 4 | 代表年校准 | 需要长期气候代表性时 | `process representative-year` |

### 典型场景组合

**场景一：多塔项目，短期缺失**

```
clean → tower-shading → reconstruct-single → reconstruct-cross → report
```

**场景二：单塔项目，长期缺失**

```
clean → tower-shading → reconstruct-single → train-meso → reconstruct-meso → representative-year → report
```

**场景三：多塔项目，长期缺失**

```
clean → tower-shading → reconstruct-single → train-reconstruct-cross → reconstruct-cross → train-meso → reconstruct-meso → representative-year → report
```

## 质量评估指标

### 重构成功率

| 指标 | 计算方式 | 理想值 |
|------|----------|--------|
| 填充率 | 成功填补数 / 原始缺失数 | 接近 100% |
| 重构成功率 | 成功重构数 / 尝试重构数 | > 80% |
| 覆盖率 | 有效数据数 / 理论数据数 | > 95% |

### 相关性指标

| 指标 | 计算方式 | 解读 |
|------|----------|------|
| 皮尔逊相关系数 | 目标值与源值线性相关程度 | > 0.8 为高相关 |
| 风向标准差 | 风向重构的离散程度 | < 12.5° 为良好 |
| 平均相关系数 | 多塔模型的平均相关性 | > 0.7 为可用 |

### 统计特征对比

| 指标 | 对比内容 |
|------|----------|
| 平均风速 | 重构后与原始数据的均值偏差 |
| 风速标准差 | 重构后与原始数据的离散程度 |
| 极值分布 | 极端风速的分布特征对比 |

## 注意事项

### 数据质量前提

1. 所有重构方法都假设输入数据已完成清理
2. 明显的异常值应在重构前处理
3. 塔影效应应在重构前校正

### 结果验证

1. 建议对重构结果进行合理性检查
2. 对比重构数据与原始数据的统计特征
3. 关注极端天气事件期间的重构质量

### 局限性

1. 极端天气事件期间相关性可能减弱
2. 静风条件下风向重构不确定性显著增加
3. 传感器全部失效的高度层无法进行重构

## 相关文档

- [单测风塔重构算法](../technical/algorithms/reconstruct-single.md)
- [跨测风塔重构算法](../technical/algorithms/reconstruct-cross.md)
- [中尺度数据重构算法](../technical/algorithms/reconstruct-meso.md)
- [代表年校准算法](../technical/algorithms/representative-year.md)
- [重构单配置说明](../user/configuration/config-files/reconstruct-single.md)
- [重构跨配置说明](../user/configuration/config-files/reconstruct-cross.md)
- [重构中尺度配置说明](../user/configuration/config-files/reconstruct-meso.md)
- [代表年配置说明](../user/configuration/config-files/representative-year.md)
