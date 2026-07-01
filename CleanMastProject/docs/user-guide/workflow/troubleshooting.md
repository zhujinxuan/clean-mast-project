# 故障排除指南

本指南帮助用户诊断和解决 CleanMast 使用过程中遇到的常见问题。

## 安装问题

### Julia 环境问题

**问题表现**：`mise run bootstrap` 失败。

**解决方法**：
1. 确认 mise 已安装：运行 `mise --version` 检查
2. 如果 Julia 或 Python 未安装，运行 `mise install` 获取所需运行时
3. 确认在项目根目录下运行 `mise run bootstrap`
4. 检查网络连接，确保能访问 Julia 和 Python 包仓库

**问题表现**：运行 `julia --version` 提示找不到命令。

**解决方法**：
1. 运行 `mise install` 安装 Julia（推荐）或手动安装 Julia 1.9+
2. 检查系统 PATH 环境变量是否包含 Julia 的 bin 目录
3. 重启终端或命令提示符使环境变量生效

**问题表现**：`using CleanMast` 提示找不到包。

**解决方法**：
1. 运行 `mise run bootstrap` 安装所有依赖
2. 或手动操作：进入项目目录后运行 `julia --project=. -e 'import Pkg; Pkg.instantiate()'`
3. 等待依赖包下载安装完成

**问题表现**：包预编译失败或超时。

**解决方法**：
1. 删除 `~/.julia/packages` 中对应的缓存目录
2. 重新运行 `julia --project=. -e 'import Pkg; Pkg.precompile()'`
3. 如仍有问题，检查网络连接或代理设置

## 配置文件错误

### TOML 解析错误

**错误信息**：`ERROR: TOML Parser Error: ...`

**常见原因**：
- TOML 语法错误，如引号使用不当
- 键名重复
- 数组格式错误

**解决方法**：
1. 使用 TOML 验证工具检查配置文件语法
2. 确认字符串使用双引号，数组使用方括号
3. 检查是否有重复的键名

**配置示例**：

```toml
# 正确格式
[sensorColumns]
windSpeed_80m = { columnName = "WS_80m_avg", height = 80.0, sensorType = "WindSpeed", statType = "avg" }

# 常见错误：缺少引号
windSpeed_80m = { columnName = WS_80m_avg, ... }  # 错误

# 常见错误：键名重复
[sensorColumns]
[sensorColumns]  # 错误
```

### 传感器列配置错误

**错误信息**：`ERROR: load config error: ...`

**常见原因**：
- `columnName` 指定的列名在数据文件中不存在
- `sensorType` 值不合法
- `height` 值类型错误

**解决方法**：
1. 确认数据文件的实际列名（区分大小写）
2. 检查 `sensorType` 是否为 `"WindSpeed"`、`"WindDirection"`、`"Temperature"`、`"Pressure"` 之一
3. 确保 `height` 为数值类型

**配置示例**：

```toml
[[sensorColumns]]
columnName = "WindSpeed_80m_avg"  # 必须与数据文件列名完全一致
height = 80.0
sensorType = "WindSpeed"  # 正确的传感器类型
statType = "avg"  # 当前仅支持 "avg"
```

### 文件路径配置错误

**错误信息**：`ERROR: could not open file ...`

**常见原因**：
- 配置文件路径不存在
- 相对路径使用错误
- Windows 路径格式问题

**解决方法**：
1. 使用绝对路径或相对于项目根目录的路径
2. Windows 系统路径使用双反斜杠或正斜杠：`C:\\path\\to\\file` 或 `C:/path/to/file`
3. 确认文件存在且有读取权限

## 数据解析失败

### CSV 读取错误

**错误信息**：`ERROR: CSV.Error: ...`

**常见原因**：
- 文件编码不支持（常见 GBK 编码文件）
- 列数不匹配
- 数据格式异常

**解决方法**：
1. 使用 `preprocess-tools` 将数据转换为 UTF-8 编码
2. 检查配置文件中的 `delimiter` 设置是否正确
3. 确认数据文件是否有表头行

**配置示例**：

```toml
[dataSource]
fileType = "csv"
delimiter = ","  # 根据实际文件调整
headerRows = 1   # 表头行数
encoding = "utf-8"  # 指定编码
```

### 时间戳解析错误

**错误信息**：`ERROR: ArgumentError: unable to parse date ...`

**常见原因**：
- 时间格式与配置不符
- 时区信息缺失
- 日期超出有效范围

**解决方法**：
1. 检查 `timestampFormat` 配置是否正确
2. 常见格式：`"yyyy-mm-dd HH:MM:SS"`、`"yyyy/mm/dd HH:MM:SS"`
3. 确认数据中的时间戳完整无缺失

**配置示例**：

```toml
[dataSource]
timestampColumn = "timestamp"
timestampFormat = "yyyy-mm-dd HH:MM:SS"
timezone = "UTC+8"  # 或 "UTC"
```

### 缺失传感器列

**错误信息**：`ERROR: KeyError: key ... not found`

**常见原因**：
- 配置中指定的列名在数据文件中不存在
- 数据文件列名与配置不一致
- 数据预处理后列名发生变化

**解决方法**：
1. 使用 `CleanMast recommend sensors` 命令查看数据文件的实际列名
2. 核对 `columnName` 与数据文件列名是否完全一致（包括大小写）
3. 检查是否需要使用 `columnMapping` 进行列名映射

## 数据处理错误

### 范围验证失败

**错误信息**：`ERROR: Value out of range: wind_speed = ...`

**常见原因**：
- 风速数据超出合理范围（通常 0-50 m/s）
- 风向数据超出 0-360 度范围
- 温度、气压数据超出物理合理范围

**解决方法**：
1. 检查原始数据是否存在错误或传感器故障
2. 调整 `rangeConfig` 中的 `validRange` 设置
3. 查看数据质量报告确认问题范围

**配置示例**：

```toml
[dataValidation]
[dataValidation.windSpeedRange]
columnPattern = "WindSpeed.*"
validRange = [0.0, 50.0]
action = "flag"  # 或 "remove"、"interpolate"
```

### 层差检查失败

**错误信息**：`ERROR: Layer difference exceeds threshold`

**常见原因**：
- 上下层风速变化率过大
- 传感器安装位置异常
- 数据采集错误

**解决方法**：
1. 检查传感器安装高度和位置是否正确
2. 调整 `layerDifferenceConfig` 中的 `maxDifference` 阈值
3. 考虑使用 `icingDetection` 功能检测传感器结冰

**配置示例**：

```toml
[dataValidation]
[dataValidation.layerDifference]
maxDifference = 10.0  # m/s
heightPairs = [[10.0, 40.0], [40.0, 80.0], [80.0, 100.0]]
```

### 塔影效应检测失败

**错误信息**：`ERROR: Tower shadow correction failed`

**常见原因**：
- 没有配置塔影传感器
- 数据时间序列不连续
- 风向数据缺失

**解决方法**：
1. 确认已正确配置塔影检测传感器
2. 检查 `towerShadingConfig` 设置
3. 确保风向数据完整可用

## 缺失数据处理

### 连续缺失数据

**问题表现**：处理结果中出现大段连续 `missing` 值。

**解决方法**：
1. 使用 `gapFillingConfig` 配置插值方法
2. 考虑使用 `ReconstructSingleMast` 或 `ReconstructMeso` 进行数据填补
3. 调整 `maxConsecutiveMissing` 阈值

**配置示例**：

```toml
[dataReconstruction]
[gapFilling]
method = "linear"  # "linear"、"spline"、"nearest"
maxGapLength = 6   # 最大允许填补的连续缺失数
```

### 全部数据缺失

**问题表现**：某个传感器所有数据均为 `missing`。

**解决方法**：
1. 检查原始数据文件是否为空或格式错误
2. 确认 `columnName` 配置正确
3. 使用 `recommend sensors` 命令验证传感器识别结果
4. 如传感器确实故障，考虑从配置中移除或使用其他高度数据

## 运行时常见错误

### 内存不足

**错误信息**：`ERROR: OutOfMemoryError()`

**解决方法**：
1. 减少单次处理的数据量，分批处理
2. 增加 Julia 内存限制：`julia --heap-size-hint=8G`
3. 使用 64 位 Julia 版本
4. 考虑使用 `DataFramesMeta.@chain` 优化内存使用

### 脚本执行超时

**问题表现**：处理命令长时间无响应。

**解决方法**1. 使用 `time` 命令监控处理进度
2. 检查数据文件大小，考虑分批处理
3. 查看是否有死循环或无限等待
4. 使用 `--verbose` 参数查看详细日志

### 输出文件生成失败

**错误信息**：`ERROR: could not open file ... for writing`

**解决方法**：
1. 确认输出目录存在且有写入权限
2. 检查磁盘空间是否充足
3. 关闭可能正在使用输出文件的其他程序
4. 使用绝对路径指定输出位置

## 获取帮助

### 调试模式

使用 Justfile 中的 recipe 运行处理步骤。如需添加 `--verbose` 或 `--debug` 参数获取详细日志，
可以编辑项目中的 Justfile，在对应 recipe 的命令中添加相应参数：

```bash
cd projects/<project-name>
just process-clean
```
### 检查配置

使用 Justfile 中的 `recommend` recipe 验证配置和传感器：

```bash
cd projects/<project-name>
just recommend-parse-sensors
just recommend-clean
```

所有 `just recommend-*` recipe 会生成推荐的配置文件，可复制到项目目录后继续使用。
### 查看日志

处理过程中生成的日志文件位于：

```bash
logs/
├── process_YYYYMMDD.log
└── error_YYYYMMDD.log
```

### 社区支持

如问题仍未解决，请提供以下信息：

1. 操作系统和 Julia 版本
2. 完整的错误信息和日志
3. 配置文件（脱敏后）
4. 数据文件样本（可匿名化处理）
