# WTTimeSeries 组件

## 概述

WTTimeSeries 组件用于从代表性年数据中提取指定高度的风速和风向数据，生成符合 Meteodyn WT 软件输入格式的时间序列文件。该组件主要用于风电机组载荷计算和发电量估算。

## 职责

- 解析 wt-timeseries.toml 配置文件
- 为每个测风塔和目标高度组合查找最近的可用传感器
- 提取风速（WindSpeed）和风向（WindDirection）数据
- 生成标准化的时间序列 CSV 文件

## 输入

- **配置文件**: wt-timeseries.toml
  - 包含多个测风塔的配置信息
  - 每个测风塔指定：输入数据源、目标高度列表、输出目录
- **代表性年数据**: 从 RepresentativeYear 组件生成的输出文件

## 输出

- **CSV 文件**: `{mast_name}-{height}m.csv`
  - timestamp: 时间戳（yyyy-mm-dd HH:MM:ss 格式）
  - wind_speed: 风速数据
  - wind_direction: 风向数据
  - 文件保存至配置的输出目录

## 依赖

- **上游组件**: RepresentativeYear（提供处理后的时间序列数据）
- **外部工具**: Meteodyn WT（用于风电机组载荷计算和发电量估算）
- **配置类型**: WtTimeSeriesConfiguration, WtTimeSeriesMast
