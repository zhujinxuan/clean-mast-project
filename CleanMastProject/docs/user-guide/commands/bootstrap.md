# bootstrap 命令参考

`bootstrap` 命令用于从现有数据快速生成配置文件模板。

## 命令列表

| 命令 | 功能描述 |
|------|----------|
| [guess-mast-from-meso](#guess-mast-from-meso) | 生成 guess-mast-from-meso.toml 配置模板 |

---

## guess-mast-from-meso

从中尺度数据生成 `guess-mast-from-meso.toml` 配置模板。

**用法：**
```bash
julia bin/CleanMast.jl bootstrap guess-mast-from-meso --meso ./raw/era5.csv
julia bin/CleanMast.jl bootstrap guess-mast-from-meso --meso ./raw/era5.csv --output ./config/era5-guess.toml
```

**参数：**
- `--meso`：中尺度数据 CSV 文件路径（传感器文件自动检测为 `basename.sensors.toml`）
- `--output`：配置文件输出路径（默认：相对于中尺度目录的 `../{中尺度基础名}.guess-mast-from-meso.toml`）

**功能：**
生成不完整的配置文件，包含需要手动填充的 TODO 字段。

**输出文件：**
- `./guessed-masts/{中尺度基础名}-vm.csv`
- `./guisted-masts/{中尺度基础名}-vm.sensors.toml`

---

## 工作流程

```
┌─────────────────┐
│  中尺度数据文件  │
│  era5.csv       │
└────────┬────────┘
         │
         │ bootstrap guess-mast-from-meso
         │ --meso ./raw/era5.csv
         ▼
┌─────────────────┐
│  配置文件模板   │
│  era5.guess-    │
│  mast-from-     │
│  meso.toml      │
│  (含 TODO 字段) │
└────────┬────────┘
         │
         │ 手动编辑 TODO 字段
         │ 设置目标平均风速等
         ▼
┌─────────────────┐
│  完整配置       │
│  era5.guess-    │
│  mast-from-     │
│  meso.toml      │
└────────┬────────┘
         │
         │ guess mast-from-meso
         ▼
┌─────────────────┐
│  合成塔数据     │
│  era5-vm.csv    │
│  era5-vm.      │
│  sensors.toml   │
└─────────────────┘
```

---

## 生成的配置模板示例

```toml
# era5.guess-mast-from-meso.toml

[meso]
data_path = "./mesos/era5.csv"
sensors_path = "./mesos/era5.sensors.toml"

[targets]
# TODO: 设置各高度的目标平均风速（m/s）
height_100m = 0.0  # 需要填入目标值
height_80m = 0.0   # 需要填入目标值
height_60m = 0.0   # 需要填入目标值
height_40m = 0.0   # 需要填入目标值
height_10m = 0.0   # 需要填入目标值

[output]
directory = "./guessed-masts"
base_name = "era5-vm"

# TODO: 根据需要调整以下参数
[parameters]
# 风速缩放方法
method = "mean_speed_matching"

# 方向保持
preserve_direction = true

# 统计类型
stat_type = "avg"
```

---

## 手动填充字段说明

| 字段 | 描述 | 填值建议 |
|------|------|----------|
| `targets.height_*` | 各高度的目标平均风速 | 基于工程估算或类似项目经验 |
| `output.directory` | 输出目录 | 默认为 `./guessed-masts` |
| `output.base_name` | 输出文件基础名 | 建议使用有意义的名称 |

---

## 使用示例

**完整工作流程：**

```bash
# 1. 假设有中尺度数据
ls ./mesos/
# era5.csv
# era5.sensors.toml

# 2. 生成配置模板
julia bin/CleanMast.jl bootstrap guess-mast-from-meso --meso ./mesos/era5.csv

# 3. 编辑生成的配置文件
# 使用文本编辑器填充 TODO 字段

# 4. 运行 guess 命令生成合成数据
julia bin/CleanMast.jl guess mast-from-meso ./mesos/era5.guess-mast-from-meso.toml

# 5. 查看生成的合成塔数据
ls ./guessed-masts/
# era5-vm.csv
# era5-vm.sensors.toml
```

---

## 自动检测逻辑

- **传感器文件**：自动将 `{meso}.csv` 转换为 `{meso}.sensors.toml`
- **输出路径**：
  - 如果未指定 `--output`，默认输出到 `{meso_dir}/../{meso_basename}.guess-mast-from-meso.toml`
  - 例如：`./mesos/era5.csv` → `./era5.guess-mast-from-meso.toml`

---

## 与 guess 命令的关系

```
bootstrap guess-mast-from-meso
         │
         │ 生成模板
         ▼
guess-mast-from-meso.toml (有 TODO)
         │
         │ 手动编辑
         ▼
guess-mast-from-meso.toml (完整)
         │
         │ guess mast-from-meso
         ▼
合成塔数据文件
```

**要点：**
- `bootstrap` 生成模板（包含 TODO）
- `guess mast-from-meso` 使用完整配置生成实际数据
- 两者配合使用，流程更清晰

---

## 注意事项

1. **必须手动编辑**：bootstrap 生成的配置需要手动填充 TODO 字段
2. **目标风速估算**：目标平均风速应基于可靠信息源
3. **文件路径**：确保中尺度 CSV 和传感器 TOML 文件在同一目录
4. **后续处理**：生成的合成数据可以用于后续的 `parse-sensors` 处理
