# recommend reconstruct-single

## 概述

生成单测风塔重构的配置文件，利用同一测风塔不同高度传感器间的相关性来填补数据缺失。

## 语法

```bash
julia bin/CleanMast.jl recommend reconstruct-single <项目目录>
```

## 实现位置

**核心实现**: `src/ReconstructSingleMast/RecommendReconstructSingleCommand.jl`

## 功能流程

1. **依赖检查**
   - 读取 `tower-shading.toml` 配置
   - 验证塔影校正后的数据文件
   - 分析传感器高度配置

2. **相关性分析**
   - 计算不同高度传感器间的相关性
   - 识别最佳参考传感器组合
   - 评估数据重构的可行性

3. **配置生成**
   - 创建单测风塔重构条目
   - 设置适当的输入输出路径
   - 配置重构参数和方法

4. **输出文件**
   - 生成 `reconstruct-single.toml` 配置文件

## 相关文件

- **配置文件**: reconstruct-single.toml (待创建配置文档)
- **处理命令**: [process reconstruct-single](../process/reconstruct-single.md)
- **配置类型**: `src/Types/ReconstructSingleConfig.jl`
- **技术实现**: [单测风塔重构算法](../../../technical/algorithms/reconstruct-single.md)

## 输出配置示例

```toml
# reconstruct-single.toml
# 基于实际项目结构: projects/pn-3masts/reconstruct-single.toml
# 使用同一测风塔传感器间相关性填补缺失数据

[[masts]]
name = "测风塔01"

    [masts.input]
    data = "./tower-shading/测风塔01.csv"
    sensors = "./tower-shading/测风塔01.sensors.yaml"

    [masts.output]
    data = "./reconstruct-single/测风塔01.csv"
    sensors = "./reconstruct-single/测风塔01.sensors.yaml"

[[masts]]
name = "测风塔02"

    [masts.input]
    data = "./tower-shading/测风塔02.csv"
    sensors = "./tower-shading/测风塔02.sensors.yaml"

    [masts.output]
    data = "./reconstruct-single/测风塔02.csv"
    sensors = "./reconstruct-single/测风塔02.sensors.yaml"
```

## 下一步操作

配置生成后，可以执行以下步骤：

1. **检查配置**: 验证重构参数和传感器配对
2. **执行重构**: `julia bin/CleanMast.jl process reconstruct-single ./project/reconstruct-single.toml`
3. **质量评估**: `julia bin/CleanMast.jl analyze reconstruct-single ./project`
4. **生成下一步配置**: `julia bin/CleanMast.jl recommend train-meso ./project`

## 注意事项

- 需要先完成塔影校正步骤
- 重构质量依赖于传感器间的相关性