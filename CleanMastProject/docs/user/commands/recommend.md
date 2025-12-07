# recommend 命令

## 概览

`recommend` 命令组用于自动生成各种处理步骤的配置文件。这些命令分析现有数据和项目状态，自动创建适当的配置文件，简化工作流程。

## 工作原理

`recommend` 命令遵循智能配置生成原则：
1. **分析现有数据** - 扫描项目目录，识别可用的数据源
2. **确定依赖关系** - 确保配置引用正确的输入文件
3. **生成最佳实践配置** - 创建包含推荐设置的配置文件
4. **支持后续步骤** - 为下一个处理步骤做准备
5. **路径自动调整** - 报告配置使用配置文件相对路径，保证位置独立性

## 命令列表

### recommend process-clean

生成数据清理处理的配置文件。

#### 语法
```bash
julia bin/CleanMast.jl recommend process-clean <项目目录>
```

#### 功能
1. 读取 `parse-sensors.toml` 文件
2. 识别测风塔数据源（时间跨度<5年）
3. 设置输入路径为 `parse-sensors` 步骤的输出
4. 配置默认清理规则文件
5. 生成 `process-clean.toml` 配置

#### 输出配置示例
```toml
[[masts]]
name = "测风塔01"

[masts.input]
data = "raw/测风塔01.csv"
sensors = "raw/测风塔01.sensors.toml"

[masts.output]
data = "./clean/测风塔01.csv"
sensors = "./clean/测风塔01.sensors.toml"

rules = "formats/clean/default.toml"
```

---

### recommend tower-shading

生成塔影校正处理的配置文件。

#### 语法
```bash
julia bin/CleanMast.jl recommend tower-shading <项目目录>
```

#### 功能
1. 读取 `process-clean.toml` 配置
2. 为每个测风塔创建塔影校正条目
3. 设置输入路径为数据清理步骤的输出
4. 配置默认输出路径
5. 生成 `tower-shading.toml` 配置

#### 输出配置示例
```toml
[[masts]]
name = "测风塔01"

[masts.input]
data = "./clean/测风塔01.csv"
sensors = "./clean/测风塔01.sensors.yaml"

[masts.output]
data = "./tower-shading/测风塔01.csv"
sensors = "./tower-shading/测风塔01.sensors.yaml"
```

---

### recommend reconstruct-single

生成单测风塔重构的配置文件。

#### 语法
```bash
julia bin/CleanMast.jl recommend reconstruct-single <项目目录>
```

#### 功能
1. 读取 `tower-shading.toml` 配置
2. 创建单测风塔重构条目
3. 设置适当的输入输出路径
4. 生成 `reconstruct-single.toml` 配置

#### 输出配置示例
```toml
[[masts]]
name = "测风塔01"

[masts.input]
data = "./tower-shading/测风塔01.csv"
sensors = "./tower-shading/测风塔01.sensors.yaml"

[masts.output]
data = "./reconstruct-single/测风塔01.csv"
sensors = "./reconstruct-single/测风塔01.sensors.yaml"
```

---

### recommend train-meso

生成中尺度模型训练的配置文件。

#### 语法
```bash
julia bin/CleanMast.jl recommend train-meso <项目目录>
```

#### 功能
1. 读取塔影校正配置获取测风塔数据路径
2. 读取 `parse-sensors.toml` 识别中尺度数据源
3. 为所有测风塔-中尺度组合创建模型训练条目
4. 配置多种模型类型（16扇区、1扇区、常数偏移）
5. 生成 `train-meso.toml` 配置

#### 生成的模型类型
- **风速模型**: 16扇区和1扇区线性回归
- **风向模型**: 常数偏移校正

#### 输出配置示例
```toml
[[masts]]
name = "测风塔01"
data = "./tower-shading/测风塔01.csv"
sensors = "./tower-shading/测风塔01.sensors.yaml"

[[mesos]]
name = "era5"
data = "./raw/era5.csv"
sensors = "./raw/era5.sensors.toml"

# 为每个测风塔-中尺度组合生成模型
[[models]]
mast_name = "测风塔01"
meso_name = "era5"
method = "16-sector"
output = "./meso-models/测风塔01/era5/windspeed/16-sector.jld2"

[[models]]
mast_name = "测风塔01"
meso_name = "era5"
method = "constant-offset"
output = "./meso-models/测风塔01/era5/winddirection/constant-offset.jld2"
```

---

### recommend reconstruct-meso

生成中尺度重构的配置文件（基于训练结果）。

#### 语法
```bash
julia bin/CleanMast.jl recommend reconstruct-meso <项目目录>
```

#### 功能
1. 分析训练好的中尺度模型
2. 读取模型性能指标
3. 为每个目标选择最佳模型
4. 生成智能的重构配置

---

### recommend report-all

生成所有报告配置文件的统一命令。

#### 语法
```bash
julia bin/CleanMast.jl recommend report-all <项目目录>
```

#### 生成的配置
- `report-timeseries-meso.toml` - 中尺度重构数据分析
- `report-timeseries-rep.toml` - 代表年数据分析
- `report-recovery.toml` - 数据恢复分析
- `report-cross-mast.toml` - 跨塔相关性分析
- `report-reconstruct-single.yaml` - 单塔重构分析

---

### recommend analyze-reconstruct-single

生成单测风塔重构分析的配置文件。

#### 语法
```bash
julia bin/CleanMast.jl recommend analyze-reconstruct-single <项目目录>
```

#### 功能
1. 识别重构前数据（塔影校正后）
2. 识别重构后数据（单测风塔重构后）
3. 配置对比分析参数
4. 生成分析配置

#### 输出配置示例
```yaml
masts:
  - name: 测风塔01
    before_reconstruction:
      csv: ./tower-shading/测风塔01.csv
      sensorConfig: ./tower-shading/测风塔01.sensors.yaml
    after_reconstruction:
      csv: ./reconstruct-single/测风塔01.csv
      sensorConfig: ./reconstruct-single/测风塔01.sensors.yaml
output:
  dir: ./analyze-reconstruct-single
```

## 三步工作流程模式

大多数功能遵循三步工作流程：

### 1. 简单推荐
```bash
julia bin/CleanMast.jl recommend <功能名> <项目目录>
```
基于现有数据生成基本配置。

### 2. 执行处理
```bash
julia bin/CleanMast.jl process <功能名> <项目目录>/<功能名>.toml
```
使用配置执行主要功能。

### 3. 智能推荐
```bash
julia bin/CleanMast.jl recommend <下一步功能> <项目目录>
```
基于分析结果生成优化的下一步配置。

## 工作流程示例

```bash
# 1. 初始数据清理推荐
julia bin/CleanMast.jl recommend process-clean ./project

# 2. 执行数据清理
julia bin/CleanMast.jl process clean ./project

# 3. 塔影校正推荐
julia bin/CleanMast.jl recommend tower-shading ./project

# 4. 执行塔影校正
julia bin/CleanMast.jl process tower-shading ./project/tower-shading.toml

# 5. 单测风塔重构推荐
julia bin/CleanMast.jl recommend reconstruct-single ./project

# 6. 执行单测风塔重构
julia bin/CleanMast.jl process reconstruct-single ./project/reconstruct-single.toml
```

## 配置文件编辑

生成的配置文件可以手动编辑以：
- 调整输出路径
- 修改处理参数
- 选择特定的数据源
- 自定义分析设置

## 最佳实践

1. **按顺序使用推荐命令** - 遵循处理流程的依赖关系
2. **检查生成的配置** - 验证路径和设置是否正确
3. **根据需要自定义** - 调整配置以满足特定需求
4. **保存配置文件** - 用于重现性和文档记录

## 注意事项

- 推荐命令依赖于之前步骤的输出
- 确保项目目录结构正确
- 检查生成的配置文件中的路径
- 某些推荐需要特定的输入文件存在