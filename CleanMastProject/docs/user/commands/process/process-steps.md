# process steps

## 概述

`process steps` 命令提供灵活的数据处理流水线控制，允许用户执行特定的处理步骤范围或完整的处理流程。

## 实现位置

**核心实现**: `src/Command/ProcessSteps.jl`

## 语法

```bash
julia bin/CleanMast.jl process steps [选项] <项目目录>
```

### 命令选项

- `--all`: 执行所有处理步骤 (1-18)
- `--from <步骤号>`: 从指定步骤开始执行 (1-18)
- `--to <步骤号>`: 执行到指定步骤结束 (1-18)
- `--list`: 仅显示所有可用步骤，不执行任何操作

## 处理步骤列表

完整的数据处理流水线包含以下 18 个步骤：

1. **recommend-clean** - 推荐数据清理配置
2. **clean** - 使用配置规则清理数据
3. **recommend-tower-shading** - 推荐塔影校正配置
4. **tower-shading** - 处理塔影校正
5. **recommend-reconstruct-single** - 推荐单测风塔重构配置
6. **reconstruct-single** - 重构单测风塔数据
7. **recommend-train-cross** - 推荐交叉测风塔训练配置
8. **train-cross** - 训练交叉测风塔重构模型
9. **recommend-reconstruct-cross** - 推荐交叉测风塔重构配置
10. **reconstruct-cross** - 重构交叉测风塔数据 [条件性]
11. **recommend-train-meso** - 推荐中尺度训练配置
12. **train-meso** - 训练中尺度重构模型
13. **recommend-reconstruct-meso** - 推荐中尺度重构配置
14. **reconstruct-meso** - 使用中尺度数据重构
15. **recommend-representative-year** - 推荐代表年配置
16. **representative-year** - 校准到代表年
17. **recommend-wt-timeseries** - 推荐风机时间序列配置
18. **wt-timeseries** - 生成 MeteoDyn 风机时间序列数据

## 使用示例

### 执行所有步骤
```bash
julia bin/CleanMast.jl process steps --all projects/windfarm-170
```

### 查看所有可用步骤
```bash
julia bin/CleanMast.jl process steps --list
```

### 执行特定步骤范围
```bash
# 执行步骤 5-12 (单测风塔重构到中尺度训练)
julia bin/CleanMast.jl process steps --from 5 --to 12 projects/windfarm-170

# 从步骤 10 开始执行到结束
julia bin/CleanMast.jl process steps --from 10 projects/windfarm-170

# 执行步骤 1-8 (数据清理到交叉测风塔训练)
julia bin/CleanMast.jl process steps --to 8 projects/windfarm-170
```

### 调试和错误恢复场景
```bash
# 如果处理在步骤 12 失败，可以从该步骤重新开始
julia bin/CleanMast.jl process steps --from 12 projects/windfarm-170

# 仅执行数据准备步骤 (1-6)
julia bin/CleanMast.jl process steps --from 1 --to 6 projects/windfarm-170

# 仅执行模型训练步骤 (7-12)
julia bin/CleanMast.jl process steps --from 7 --to 12 projects/windfarm-170
```

## 输出示例

```bash
$ julia bin/CleanMast.jl process steps --from 5 --to 8 projects/windfarm-170

Processing steps 5-8 for project: projects/windfarm-170
Total steps to execute: 4

5. Recommend single mast reconstruction configuration...
   ✅ Step 5 completed successfully

6. Reconstruct single mast data...
   ✅ Step 6 completed successfully

7. Recommend cross-mast training configuration...
   ✅ Step 7 completed successfully

8. Train cross-mast reconstruction models...
   ✅ Step 8 completed successfully

🎉 Processing completed successfully!
Executed steps 5-8 (4 steps total)
```

## 错误处理和恢复

如果处理过程中出现错误，命令会显示详细的错误信息和恢复建议：

```bash
❌ Processing stopped at step 12 due to error:
   Configuration file not found: train-meso.toml

Completed: 11/18 steps
To resume, use: process steps --from 12
```


## 前置条件

- 必须先完成 `project parse-sensors` 步骤
- 项目目录中需要有原始数据文件
- 中尺度再分析数据可用（用于模型训练步骤）

## 输出结构

完整处理流程会生成以下目录结构：

```
project/
├── raw/                     # 原始数据 (输入)
├── clean/                   # 清理后数据
├── tower-shading/           # 塔影校正后数据
├── reconstruct-single/      # 单塔重构后数据
├── train-reconstruct-cross/ # 交叉测风塔训练结果
├── reconstruct-cross/       # 交叉测风塔重构数据
├── meso-models/            # 训练的中尺度模型
├── reconstruct-meso/       # 中尺度重构后数据
├── representative-year/     # 代表年校准数据
├── wt-timeseries/          # 风机时间序列 (Meteodyn格式)
└── *.toml                  # 各步骤配置文件
```

## 相关命令

如需单独执行特定步骤，也可以使用以下独立命令：

- [process clean](clean.md) - 数据清理
- [process tower-shading](tower-shading.md) - 塔影校正
- [process reconstruct-single](reconstruct-single.md) - 单测风塔重构
- [process train-meso](train-meso.md) - 中尺度模型训练
- [process reconstruct-meso](reconstruct-meso.md) - 中尺度重构
- [process representative-year](representative-year.md) - 代表年校准
- [process wt-timeseries](wt-timeseries.md) - 导出风机时间序列

## 注意事项

- 使用 `--list` 选项查看所有可用步骤和其描述
- 某些步骤是条件性的，如果不满足条件会自动跳过
- 检查处理日志以确认每个步骤成功完成
- 验证最终输出数据的质量和完整性
- 推荐在开发和调试时使用步骤范围功能来快速定位问题