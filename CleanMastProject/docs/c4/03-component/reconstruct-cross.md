# ReconstructCross 组件

## 概述

ReconstructCross 组件负责跨测风塔数据重建，使用 TrainReconstructCross 训练好的模型来填补目标测风塔的缺失数据。支持风速和风向两个维度的重建。

## 职责

- 加载 TrainReconstructCross 生成的模型文件
- 读取配置文件中定义的重建任务优先级
- 按优先级顺序执行重建任务，支持并行批处理
- 仅填补缺失数据点，保留原有有效数据
- 生成重建质量报告和统计摘要

## 输入

| 输入 | 类型 | 来源 |
|------|------|------|
| 配置文件 | TOML | 用户配置 (reconstruct-cross.toml) |
| 训练好的模型 | JLD2 | TrainReconstructCross 组件 |
| 测风塔时间序列 | TimeSeriesData | ReconstructSingleMast 或其他上游组件 |

## 输出

| 输出 | 类型 | 去向 |
|------|------|------|
| 重建后的时间序列 | TimeSeriesData | RepresentativeYear, Reporting |
| 重建摘要报告 | TOML | 报告生成 |
| 质量指标 | 统计数据 | 质量评估 |

## 依赖关系

```
TrainReconstructCross → ReconstructCross → RepresentativeYear
```

- **上游**: TrainReconstructCross 提供训练好的模型；ReconstructSingleMast 提供时间序列数据
- **下游**: RepresentativeYear 进行长期校准，Reporting 生成报告

## 配置接口

使用 `reconstruct-cross.toml` 定义重建任务、优先级设置和输入输出路径。

## 注意事项

- 重建任务按优先级执行（高相关性优先）
- 仅填补缺失数据，保留原有有效测量值
- 需要预先完成 TrainReconstructCross 训练阶段
- 支持批量并行处理多个重建任务
