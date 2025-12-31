# project 命令

## 概览

`project` 命令组用于项目管理，主要提供传感器数据解析功能。

> **注意**: 项目初始化功能已迁移到 Python CLI，请使用 `uv run cleanmast init` 命令。

## 命令列表

### project parse-sensors

基于 TOML 配置文件处理传感器数据，创建原始数据文件和传感器元数据文件。

#### 语法
```bash
julia bin/CleanMast.jl project parse-sensors <配置文件路径>
```

#### 参数
- `配置文件路径`: parse-sensors.toml 配置文件的路径

#### 前置条件
- 必须存在有效的 `parse-sensors.toml` 配置文件
- 原始数据文件必须在配置文件中指定的位置
- 传感器格式文件必须正确配置

#### 功能
1. 读取 `parse-sensors.toml` 配置
2. 解析指定的原始数据文件
3. 应用传感器格式映射
4. 生成标准化的 CSV 文件
5. 创建传感器元数据文件

#### 输出
- `raw/<数据源名称>.csv`: 标准化的时间序列数据
- `raw/<数据源名称>.sensors.toml`: 传感器配置元数据

#### 示例
```bash
julia bin/CleanMast.jl project parse-sensors path/to/project/parse-sensors.toml
```

#### 配置文件格式

`parse-sensors.toml` 文件示例：

```toml
# 测风塔数据源
[[masts]]
input = "nrg-17005.txt"
name = "nrg-17005"
sensor = "formats/sensor/nrg.toml"
output = { data = "raw/nrg-17005.csv", sensors = "raw/nrg-17005.sensors.toml" }

# 中尺度数据源
[meso]
input = "era5.txt"
name = "era5"
sensor = "formats/sensor/freemeso-meso.toml"
output = { data = "raw/era5.csv", sensors = "raw/era5.sensors.toml" }
```

## 典型工作流程

1. **初始化项目**（使用 Python CLI）：
   ```bash
   uv run cleanmast init projects/my-project
   ```

2. **准备数据**：
   - 将原始数据文件复制到项目目录
   - 检查传感器格式文件是否正确

3. **配置解析**：
   - 编辑 `parse-sensors.toml` 文件
   - 确保所有路径和配置正确

4. **解析传感器数据**：
   ```bash
   julia bin/CleanMast.jl project parse-sensors projects/my-project/parse-sensors.toml
   ```

## 注意事项

- 确保所有原始数据文件在解析之前都存在
- 传感器格式文件必须与数据文件的列结构匹配
- 解析后的数据将用于后续的数据处理步骤
- 检查输出日志以确认解析成功完成

## 错误排除

**常见问题**：
- **文件未找到**: 检查配置文件中的路径是否正确
- **格式不匹配**: 验证传感器格式文件是否与数据文件列对应
- **权限错误**: 确保对输出目录有写入权限

**解决方案**：
- 验证所有文件路径
- 检查传感器格式配置
- 确认目录权限设置正确