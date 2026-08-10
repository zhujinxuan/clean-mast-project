## Purpose

Fifty-year max wind (extreme wind) analysis for wind resource reports. Covers IEC 61400-1 Methods 1/2/3, Gumbel distribution fitting, and IEC wind class classification.

## Rules

- Inherits all rules from `reporting/spec.md` (which inherits `subdomains/spec.md`).

## Anti-patterns

- `Path()` sentinel replaced — Q-Q subgrid functions use proper altair types.

## When in doubt

- IEC standards table is not mast-specific → assembled as NoMast atom.

## 业务说明 (Business description)

### Domain context

极端风速分析预测 N 年重现期的最大风速，使用 Gumbel 极值分布拟合年最大值序列。

### Key concepts

典型重现期: 50 年 (风机设计寿命)。

### Business constraints

样本量不足 (少于 10 年数据) 时重现期估计不可靠。
