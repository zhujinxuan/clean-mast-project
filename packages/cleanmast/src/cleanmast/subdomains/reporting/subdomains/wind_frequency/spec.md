## Purpose

Single-mast wind speed frequency distribution analysis for wind resource reports.

## Rules

- Inherits all rules from `reporting/spec.md` (which inherits `subdomains/spec.md`).
- Wind frequency computation uses vectorized Polars operations; no intermediate `rows: list[dict]` accumulation.

## Anti-patterns

- Stateful calculator classes.
- Building DataFrames from `list[dict]` in compute.

## 业务说明 (Business description)

### Domain context

风速频率分布直方图，按指定 bin 宽度统计各风速段的出现频率。

### Key concepts

bin 宽度默认 1 m/s；频率可表示为绝对频次或百分比。
