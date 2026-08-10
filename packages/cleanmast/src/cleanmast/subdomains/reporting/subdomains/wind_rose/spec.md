## Purpose

Wind rose frequency distribution (16-sector polar) computation and chart rendering for wind resource reports.

## Rules

- Inherits all rules from `reporting/spec.md` (which inherits `subdomains/spec.md`).
- No hardcoded angles (22.5, 16); use named constant `SECTOR_COUNT` and derive sector width.

## Anti-patterns

- `rows: list[dict]` in assemble; use typed structures.

## 业务说明 (Business description)

### Domain context

风玫瑰图展示 16 扇区的风向频率和风速分布，是风场布局优化的基础输入。

### Key concepts

扇区从正北 (0°) 开始，顺时针每 22.5° 一个扇区；每个扇区包含频率和平均风速。
