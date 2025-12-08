# Preprocess Tools Documentation

完整文档位于包目录: [packages/preprocess-tools/docs/](../../../packages/preprocess-tools/docs/)

## 快速链接

- [命令参考](../../../packages/preprocess-tools/docs/commands.md)
- [CSV 合并工具](../../../packages/preprocess-tools/docs/csv-merger.md)
- [NRG 格式规范](../../../packages/preprocess-tools/docs/nrg-format.md)
- [Lidar 格式规范](../../../packages/preprocess-tools/docs/lidar-format.md)
- [贡献指南](../../../packages/preprocess-tools/docs/contributing.md)

## 概述

Preprocess Tools 提供通用的 CSV 预处理工具:

- **编码转换**: 处理各种文件编码
- **CSV 合并**: 合并多个 CSV 文件并检测重复
- **列名标准化**: 转换为 NRG 或 Lidar 格式
- **时间戳标准化**: 统一时间戳格式
- **类型转换**: 字符串列转换为数值类型

## 安装

```bash
uv sync
```

## 使用

参见包 README: [packages/preprocess-tools/README.md](../../../packages/preprocess-tools/README.md)
