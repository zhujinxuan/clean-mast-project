# guess 命令参考

`guess` 命令用于从现有数据推断或生成合成数据配置。

## 命令列表

| 命令 | 功能描述 |
|------|----------|
| [mast-from-meso](#mast-from-meso) | 从中尺度数据生成合成塔数据 |

---

## mast-from-meso

使用平均风速匹配方法从中尺度数据生成合成塔数据。

**用法：**
```bash
julia bin/CleanMast.jl guess mast-from-meso guess-mast-from-meso.toml
```

**参数：**
- `config_path`：`guess-mast-from-meso.toml` 配置文件路径

**功能：**
通过将中尺度风速缩放到匹配目标平均值来生成合成塔数据。

**工作流程：**
1. 读取中尺度数据
2. 应用配置中的缩放因子
3. 生成合成的塔时序数据
4. 输出为标准格式

**输入配置：**
`guess-mast-from-meso.toml` 应包含：
- 中尺度数据源路径
- 目标平均风速（各高度）
- 输出文件路径
- 传感器配置

**输出文件：**
- `guessed-masts/{中尺度基础名}-vm.csv`：合成的塔数据
- `guessed-masts/{中尺度基础名}-vm.sensors.toml`：对应的传感器描述

---

## 配置文件示例

```toml
# guess-mast-from-meso.toml

[meso]
data_path = "./mesos/era5.csv"
sensors_path = "./mesos/era5.sensors.toml"

[targets]
# 目标平均风速（m/s）
# 这些值应该基于现场测量或工程估算
height_100m = 7.5
height_80m = 7.2
height_60m = 6.8
height_40m = 6.3
height_10m = 5.0

[output]
directory = "./guessed-masts"
base_name = "era5-vm"

[sensors]
# 传感器配置
# 从 meso 数据映射到合成塔传感器
```

---

## 使用场景

此命令适用于：

1. **数据稀缺地区**：当中尺度数据是唯一可用的数据源时
2. **初步规划阶段**：在建设测风塔之前生成参考数据
3. **方法验证**：比较合成数据与实际测量的差异
4. **风险评估**：在没有长期测量数据的情况下进行初步风资源评估

---

## 输出示例

生成的文件结构：

```
guessed-masts/
├── era5-vm.csv           # 合成塔时序数据
└── era5-vm.sensors.toml  # 传感器描述文件
```

其中 `era5-vm.csv` 包含：
- 时间戳列
- 各高度的风速数据（缩放到目标平均值）
- 风向数据（如适用）

---

## 注意事项

1. **目标值选择**：目标平均风速应基于可靠的工程估算或类似条件下的测量数据

2. **数据质量**：合成数据的质量取决于中尺度数据的质量和目标值的合理性

3. **后续处理**：生成的数据可以作为 `parse-sensors` 的输入进行进一步处理

4. **局限性**：
   - 仅保留中尺度的时序特征
   - 不反映局地地形效应
   - 不包含传感器特定的误差

---

## 相关命令

```bash
# 1. 先生成 guess-mast-from-meso 配置
julia bin/CleanMast.jl bootstrap guess-mast-from-meso --meso ./mesos/era5.csv

# 2. 编辑生成的配置文件

# 3. 运行 guess 命令
julia bin/CleanMast.jl guess mast-from-meso ./era5.guess-mast-from-meso.toml
```
