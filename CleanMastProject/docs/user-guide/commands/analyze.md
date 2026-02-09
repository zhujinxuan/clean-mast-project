# analyze 命令参考

`analyze` 命令用于执行专门的数据分析任务。

## 命令列表

| 命令 | 功能描述 |
|------|----------|
| [en](#en) | EN标准（土木工程载荷计算）风数据分析 |

---

## en

根据 EN 标准（土木工程载荷计算）分析风数据。

**用法：**
```bash
julia bin/CleanMast.jl analyze en path/to/analyze-en.yaml
julia bin/CleanMast.jl analyze en path/to/analyze-en.yaml --output results/
```

**参数：**
- `config_path`：`analyze-en.yaml` 配置文件路径
- `--output, -o`：结果输出目录（可选）

**输入配置：**
`analyze-en.yaml` 文件应指定：
- 多个塔及其坐标和测量高度
- 输入数据和传感器配置路径
- 可选的 GeoHash 位置编码

**功能：**
生成单个 `WindSpeedMatrix.txt` 文件，包含所有塔的数据：
- 平均风速（Vmean）
- 按方向扇区的平均风速（15度分箱）
- 按方向和风速的频率分布

**输出文件：**
- `WindSpeedMatrix.txt`：风速矩阵文件
- `{output}/`：指定输出目录下的结果（如有指定）

---

## 配置文件示例

```yaml
# analyze-en.yaml
masts:
  - name: "mast01"
    latitude: 39.9
    longitude: 116.4
    height: 100
    data_path: "./data/mast01_clean.csv"
    sensors_path: "./data/mast01.sensors.toml"

  - name: "mast02"
    latitude: 39.95
    longitude: 116.5
    height: 80
    data_path: "./data/mast02_clean.csv"
    sensors_path: "./data/mast02.sensors.toml"

output:
  geohash: "wmyg"
```

---

## 输出格式说明

生成的 `WindSpeedMatrix.txt` 包含：

| 字段 | 描述 |
|------|------|
| Vmean | 平均风速（m/s） |
| V_0_15 | 0-15度方向平均风速 |
| V_15_30 | 15-30度方向平均风速 |
| ... | ... |
| V_345_360 | 345-360度方向平均风速 |
| Freq_0_15 | 0-15度方向频率分布 |
| ... | 其他方向扇区 |

---

## 使用场景

此命令适用于：
- 土木工程结构载荷计算
- 风工程研究
- 极端风速条件分析
- 多塔风资源对比评估
