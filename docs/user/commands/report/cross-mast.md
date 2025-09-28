# report cross-mast

## 概述

生成跨测风塔相关性分析报告，评估测风塔间的数据关联性。

## 语法

```bash
julia bin/CleanMast.jl report cross-mast <配置文件路径>
```

## 功能

- **相关性分析**: 测风塔间风速风向相关性
- **数据覆盖**: 跨塔数据时间重叠分析
- **统计指标**: 相关系数、偏差统计
- **质量评估**: 跨塔重构潜力评估

## 配置文件

### report-cross-mast.toml
```toml
[[mast_pairs]]
reference_mast = "pn-002824"
target_mast = "pn-013945"
[mast_pairs.data]
reference_data = "./reconstruct-single/pn-002824.csv"
target_data = "./reconstruct-single/pn-013945.csv"

[output]
report_dir = "./report-masts/cross-mast"
report_filename = "report.typ"
```

## 输出文件

```
report-masts/cross-mast/
├── report.typ            # 主报告文件
└── plots/               # 相关性图表
```

## 配置生成

```bash
recommend report-all <项目目录>  # 自动生成配置
```