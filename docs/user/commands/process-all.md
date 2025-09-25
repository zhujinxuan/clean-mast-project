# process all

## 概述

`process all` 命令执行完整的数据处理流水线，自动运行所有必要的处理步骤，从原始数据清理到最终的代表年校准。

## 实现位置

**核心实现**: `src/Command/ProcessAll.jl`

## 处理流水线

## 语法

```bash
julia bin/CleanMast.jl process all <项目目录>
```

## 自动执行步骤

`process all` 命令按以下顺序自动执行完整的数据处理流水线：

### 1. [数据清理](process/clean.md)
- 应用传感器数值范围验证
- 执行高度间层差检查
- 检测和标记结冰条件
- 生成清理后的数据文件

### 2. [塔影校正](process/tower-shading.md)
- 识别相似高度的风速传感器
- 通过取最大值合并传感器数据
- 创建标准化的传感器名称
- 移除原始方向性传感器

### 3. [单测风塔重构](process/reconstruct-single.md)
- 识别数据缺失点
- 寻找同一测风塔上其他传感器的相关性
- 应用最佳可用模型填补缺口
- 验证重构数值的物理合理性

### 4. [中尺度模型训练](process/train-meso.md)
- 加载并对齐时间序列数据
- 确保测风塔数据的10分钟规律间隔
- 将中尺度数据插值到测风塔时间戳
- 训练指定的模型类型并保存

### 5. [中尺度重构](process/reconstruct-meso.md)
- 加载训练好的中尺度模型
- 识别剩余的数据缺口
- 生成完整年的时间序列数据

### 6. [代表年校准](process/representative-year.md)
- 使用16扇区线性回归作为校准因子
- 生成方向性校准的代表年数据集

### 7. [导出Meteodyn时间序列](process/wt-timeseries.md)
- 导出Meteodyn兼容格式时间序列
- 导出120m以上或者最高两层高度的风速风向

## 前置条件

- 必须先完成 `project parse-sensors` 步骤
- 项目目录中需要有原始数据文件
- 中尺度再分析数据可用（用于模型训练）

## 示例用法

```bash
# 执行完整处理流程
julia bin/CleanMast.jl process all projects/windfarm-170

# 输出示例
Processing project: projects/windfarm-170
Step 1/7: Data cleaning...            ✓ Complete
Step 2/7: Tower shading correction... ✓ Complete
Step 3/7: Single mast reconstruction... ✓ Complete
Step 4/7: Mesoscale model training...  ✓ Complete
Step 5/7: Mesoscale reconstruction...  ✓ Complete
Step 6/7: Representative year...       ✓ Complete
Step 7/7: Export WT time series...    ✓ Complete

All processing steps completed successfully!
```

## 相关命令

如需单独执行特定步骤，可使用以下独立命令：

- [process clean](process/clean.md) - 数据清理
- [process tower-shading](process/tower-shading.md) - 塔影校正
- [process reconstruct-single](process/reconstruct-single.md) - 单测风塔重构
- [process train-meso](process/train-meso.md) - 中尺度模型训练
- [process reconstruct-meso](process/reconstruct-meso.md) - 中尺度重构
- [process representative-year](process/representative-year.md) - 代表年校准
- [process wt-timeseries](process/wt-timeseries.md) - 导出风机时间序列

## 输出结构

完整处理流程会生成以下目录结构：

```
project/
├── raw/                     # 原始数据 (输入)
├── clean/                   # 清理后数据
├── tower-shading/           # 塔影校正后数据
├── reconstruct-single/      # 单塔重构后数据
├── meso-models/            # 训练的中尺度模型
├── reconstruct-meso/       # 中尺度重构后数据
├── representative-year/     # 代表年校准数据
├── wt-timeseries/          # 风机时间序列 (Meteodyn格式)
└── process-stats/          # 处理统计信息
```

## 配置管理

`process all` 会自动调用相应的 `recommend` 命令生成所需配置文件：

- `process-clean.toml`
- `tower-shading.toml`
- `reconstruct-single.toml`
- `train-meso.toml`
- `reconstruct-meso.toml`
- `representative-year.toml`
- `wt-timeseries.toml`

## 注意事项

- 检查处理日志以确认每个步骤成功完成
- 验证最终输出数据的质量和完整性