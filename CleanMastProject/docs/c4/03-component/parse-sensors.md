# ParseSensors 组件

## 概述

ParseSensors 是数据处理流水线的入口组件，负责将原始传感器数据文件转换为标准化的 `TimeSeriesData` 格式。

## 职责

- 解析原始 CSV/TXT 传感器数据文件
- 标准化时间戳格式
- 提取传感器元数据（类型、方向、高度、统计类型、单位）
- 生成标准化的时序数据结构
- 输出 Parquet 格式数据并嵌入传感器元数据

## 输入

- **数据文件**: CSV/TXT 格式的原始传感器数据
- **配置文件**: `parse-sensors.toml`（包含文件路径、传感器列定义、映射规则、时间戳配置）

## 输出

- **TimeSeriesData**: 包含标准化 DataFrame 和传感器列定义的时序数据结构
- **传感器元数据**: 嵌入 Parquet 文件的传感器配置信息

## 依赖关系

```
外部数据源 → ParseSensors → DataClean
                ↓
         TimeSeriesData
         传感器元数据
```

ParseSensors 接收原始数据文件作为输入，输出标准化的 TimeSeriesData 供下游 DataClean 组件使用。 |
