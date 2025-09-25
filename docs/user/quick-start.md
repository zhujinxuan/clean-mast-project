# CleanMast 快速开始

## 概述

本指南将带您快速完成一个完整的风资源数据处理流程，从原始数据到最终报告。

## 前置要求

- Julia 1.9+ 已安装
- CleanMast 项目已克隆到本地
- 原始测风塔数据文件（.txt/.csv 格式）
- 中尺度数据文件（ERA5 等再分析数据）

## 完整处理流程

### 1. 创建项目

```nushell
julia bin/CleanMast.jl project init projects/my-windfarm
```

### 2. 准备数据文件

将原始数据文件放置到正确位置：

```nushell
# 测风塔数据放入 masts/ 目录
mv tower1.txt projects/my-windfarm/masts/
mv tower2.txt projects/my-windfarm/masts/

# 中尺度数据放入 mesos/ 目录
mv era5-tower1.txt projects/my-windfarm/mesos/
mv era5-tower2.txt projects/my-windfarm/mesos/
```

### 3. 生成解析配置

```nushell
julia bin/CleanMast.jl recommend parse-sensors projects/my-windfarm
```

### 4. 解析原始数据

```nushell
julia bin/CleanMast.jl project parse-sensors projects/my-windfarm
```

### 5. 执行数据处理流程

```nushell
julia bin/CleanMast.jl process all projects/my-windfarm
```

这将依次执行：
- `process-clean` - 数据清理
- `tower-shading` - 塔影校正
- `reconstruct-single` - 单塔重构
- `train-reconstruct-cross` - 跨塔模型训练
- `reconstruct-cross` - 跨塔重构
- `train-meso` - 中尺度模型训练
- `reconstruct-meso` - 中尺度重构

### 6. 生成报告配置

```nushell
julia bin/CleanMast.jl recommend report-all projects/my-windfarm
```

### 7. 生成分析报告

```nushell
julia bin/CleanMast.jl report all projects/my-windfarm
```

### 8. 查看报告

使用 Typst 编译查看报告：

```nushell
# 进入报告目录
cd projects/my-windfarm/report-masts

# 编译并查看报告（具体报告文件名以生成结果为准）
typst compile data-quality-report.typ data-quality-report.pdf
```

## 输出结果

处理完成后，您将获得：

- **原始数据** (`raw/`) - 标准化后的时间序列数据
- **清理数据** (`clean/`) - 去除异常值后的数据
- **重构数据** (`reconstruct-meso/`) - 完整的长期数据序列
- **分析报告** (`report-masts/`) - 专业的风资源评估报告

## 下一步

- 查看 [命令参考](../commands/) 了解详细命令选项
- 查看 [配置指南](../configuration/) 了解配置文件自定义
- 查看生成的报告了解您的风资源特征