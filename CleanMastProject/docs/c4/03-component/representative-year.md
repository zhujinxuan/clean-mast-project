# RepresentativeYear 组件

## 概述

RepresentativeYear 是数据处理流水线的校准组件，负责将处理后的测风塔数据校准到代表性年份，用于长期风能资源评估。该组件通过中尺度数据模型建立测风塔与长期气候数据之间的关联，生成具有代表性年份特征的时间序列。

## 职责

- 加载测风塔处理后的时间序列数据
- 加载并整合多源中尺度数据
- 应用中尺度相关模型进行数据校准
- 生成代表性年份校准后的时间序列
- 保存校准结果及元数据

## 输入

- **测风塔数据**: 经过 `ReconstructMeso` 处理后的时间序列数据（Parquet 格式）
- **中尺度数据**: 来自 ReconstructMeso 输出的长期气候数据
- **配置文件**: `representative-year.toml`（包含测风塔配置、时间范围、中尺度模型文件路径）
- **训练模型**: JLD2 格式的 16 扇区风速相关模型

## 输出

- **校准时间序列**: 代表性年份校准后的 TimeSeriesData（Parquet 格式）
- **传感器配置**: 包含校准传感器元数据的 TOML 文件
- **校准信息**: 参考年份及校准传感器数量等元数据

## 依赖关系

```
ReconstructMeso → RepresentativeYear → Reporting
                     ↓
            代表年校准时间序列
```

RepresentativeYear 接收来自 ReconstructMeso 的处理后数据和中尺度数据作为输入，输出代表性年份校准后的时间序列供 Reporting 组件进行风资源分析和报告生成。
