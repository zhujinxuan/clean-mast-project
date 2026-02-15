# WTTimeSeries 组件

## 概述

WTTimeSeries 组件用于从代表性年数据中提取指定高度的风速和风向数据，生成符合 Meteodyn WT 软件输入格式的时间序列文件。该组件主要用于风电机组载荷计算和发电量估算。

## 职责

- 解析 wt-timeseries.toml 配置文件
- 为每个测风塔和目标高度组合查找最近的可用传感器
- 提取风速（WindSpeed）和风向（WindDirection）数据
- 生成标准化的时间序列 CSV 文件
- 生成湍流强度数据文件

## 输入

- **配置文件**: wt-timeseries.toml
  - 包含多个测风塔的配置信息
  - 每个测风塔指定：输入数据源、目标高度列表、输出目录
- **填充高度配置文件**: fill-heights-representative-year.toml
  - 引用填充高度模块的输出路径
- **填充后时间序列数据**: 从 FillHeights 组件生成的数据（Parquet 格式）
  - 路径: `representative-year-fill-heights/{mast}.parquet`
  - 格式: Parquet 文件，包含传感器元数据

## 输出

### CSV 时间序列文件

- **文件**: `{mast}.csv`（每个测风塔一个文件，包含所有高度）
  - 时间戳: ISO 格式（yyyy-mm-dd HH:MM:SS）
  - 列: timestamp, WindSpeed_{height}m_avg, WindDirection_{height}m_avg
  - 输出至配置的输出目录

### 湍流强度文件

- **目录**: `turbulence-{mast}/`
- **文件**: `meteodyn_ti_{height}m.txt`
  - 格式: Meteodyn WT 软件兼容格式
  - 包含各高度的湍流强度时间序列

## 高度过滤规则

- **CSV 文件高度**: 仅支持大于等于 100m 的高度
  - 需要对应高度的 WindSpeed 平均值和 WindDirection 平均值同时存在
- **湍流文件高度**: 支持任意高度
  - 需要对应高度的 WindSpeed 平均值和 WindSpeed 标准差同时存在
- CSV 和湍流文件可以使用不同的高度集合

## 依赖

- **上游组件**: FillHeights（填充高度模块）
- **外部工具**: Meteodyn WT（用于风电机组载荷计算和发电量估算）
- **配置类型**: WtTimeSeriesConfiguration, WtTimeSeriesMast

## 命令行接口

- 生成配置: `cleanmast recommend wt-timeseries <project_dir>`
- 执行处理: `cleanmast wt-timeseries <config.toml>`
