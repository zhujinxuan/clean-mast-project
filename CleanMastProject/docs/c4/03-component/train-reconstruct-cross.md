# TrainReconstructCross 组件

## 概述

TrainReconstructCross 组件负责训练跨测风塔重构模型。通过分析多个测风塔之间的风速、风向相关性，建立统计模型用于后续的数据填补。

该组件是重建管道的训练阶段，输出模型供 ReconstructCross 组件使用。

## 职责

- 加载所有测风塔的时间序列数据
- 分析所有测风塔两两组合的数据覆盖情况
- 计算风速和风向的跨塔相关系数
- 根据数据重叠天数和相关性阈值筛选合格的塔对
- 训练风速和风向的预测模型
- 将训练好的模型序列化为 JLD2 文件保存

## 输入

| 输入 | 类型 | 来源 |
|------|------|------|
| 配置文件 | TOML | 用户配置 (train-reconstruct-cross.toml) |
| 测风塔时间序列数据 | TimeSeriesData | ReconstructSingleMast 或其他上游组件 |

## 输出

| 输出 | 类型 | 去向 |
|------|------|------|
| 风速模型文件 | JLD2 | ReconstructCross 组件 |
| 风向模型文件 | JLD2 | ReconstructCross 组件 |
| 训练结果摘要 | TOML | 报告生成 |

## 依赖关系

```
ReconstructSingleMast → TrainReconstructCross → ReconstructCross
```

- **上游**: ReconstructSingleMast 提供处理后的时间序列数据
- **下游**: ReconstructCross 使用训练好的模型进行数据重建

## 配置接口

使用 `train-reconstruct-cross.toml` 定义测风塔列表、训练参数和输出目录。

## 注意事项

- 需要足够的数据重叠期（默认≥120天）才能训练可靠模型
- 风速重建要求相关系数≥0.7，风向重建要求标准差≤12.5°
- 高海拔传感器（≥120m）的相关性通常更好
- 训练结果可复用，避免重复计算
