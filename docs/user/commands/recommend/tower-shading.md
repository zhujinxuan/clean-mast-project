# recommend tower-shading

## 概述

生成塔影校正处理的配置文件，用于检测和校正测风塔对风速风向测量的影响。

## 语法

```bash
julia bin/CleanMast.jl recommend tower-shading <项目目录>
```

## 实现位置

**核心实现**: `src/TowerShading/RecommendTowerShadingCommand.jl`

## 功能流程

1. **依赖检查**
   - 读取 `process-clean.toml` 配置
   - 验证清理后的数据文件存在
   - 检查传感器配置文件

2. **配置生成**
   - 为每个测风塔创建塔影校正条目
   - 设置输入路径为数据清理步骤的输出
   - 配置默认输出路径和参数

3. **输出文件**
   - 生成 `tower-shading.toml` 配置文件

## 相关文件

- **配置文件**: tower-shading.toml (待创建配置文档)
- **处理命令**: [process tower-shading](../process/tower-shading.md)
- **配置类型**: `src/Types/TowerShadingConfig.jl`

## 输出配置示例

```toml
# tower-shading.toml
# 基于实际项目结构: projects/pn-3masts/tower-shading.toml
# 合并相近高度传感器以处理塔影效应

[[masts]]
name = "测风塔01"

    [masts.input]
    data = "./clean/测风塔01.csv"
    sensors = "./clean/测风塔01.sensors.yaml"

    [masts.output]
    data = "./tower-shading/测风塔01.csv"
    sensors = "./tower-shading/测风塔01.sensors.yaml"

[[masts]]
name = "测风塔02"

    [masts.input]
    data = "./clean/测风塔02.csv"
    sensors = "./clean/测风塔02.sensors.yaml"

    [masts.output]
    data = "./tower-shading/测风塔02.csv"
    sensors = "./tower-shading/测风塔02.sensors.yaml"
```

## 塔影检测参数

### 1. 塔影影响角度
- **默认角度范围**: ±15° (总共30°扇区)
- **可调整范围**: 10°-30°
- **影响因素**: 塔架结构、传感器安装位置

### 2. 风速衰减检测
- **最小检测风速**: 3.0 m/s (低风速下塔影效应不明显)
- **预期衰减比例**: 0.3 (30%的风速降低)
- **扇区宽度**: 22.5° (16个方向扇区)

### 3. 校正方法选项
- **sector_based**: 基于风向扇区的校正 (推荐)
- **angle_based**: 基于精确角度的校正
- **statistical**: 基于统计关系的校正

## 生成逻辑

该命令会自动：

1. **分析测风塔布局**
   - 检测传感器相对于塔身的方位角
   - 识别可能受塔影影响的传感器
   - 估算塔影影响的角度范围

2. **设置校正参数**
   - 根据塔型和传感器配置调整参数
   - 配置适当的检测阈值
   - 选择合适的校正方法

3. **配置输出结构**
   - 设置校正后数据的保存路径
   - 配置校正记录和统计输出
   - 准备后续处理步骤的输入

## 下一步操作

配置生成后，可以执行以下步骤：

1. **检查配置**: 验证塔影参数设置是否合理
2. **执行校正**: `julia bin/CleanMast.jl process tower-shading ./project/tower-shading.toml`
3. **生成下一步配置**: `julia bin/CleanMast.jl recommend reconstruct-single ./project`

## 注意事项

- 需要先完成数据清理步骤
- 塔影校正参数可能需要根据具体塔型调整
- 检查测风塔地理位置坐标的准确性
- 某些复杂塔型可能需要手动调整角度范围