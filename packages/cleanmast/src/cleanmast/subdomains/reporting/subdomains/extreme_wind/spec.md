## Purpose

Fifty-year max wind (extreme wind) analysis for wind resource reports. Covers IEC 61400-1 Methods 1/2/3, Gumbel distribution fitting, and IEC wind class classification.

## Rules

- Inherits all rules from `reporting/spec.md` (which inherits `subdomains/spec.md`).
- Q-Q subgrid helpers take and return altair chart types; the `Path()`
  no-image sentinel applies only at the atom `renderImage()` boundary
  (convention owned by reporting/spec.md).

## When in doubt

- IEC standards table is not mast-specific → assembled with
  `IECStandardsAtomMeta` (`mast_name: str = "_no_mast"`, see `model/report_meta.py`).

## 业务说明 (Business description)

### Domain context

极端风速分析预测 N 年重现期的最大风速，使用 Gumbel 极值分布拟合五日最大值序列
(五日最大法, `extract_five_day_maxima`)。

### Key concepts

典型重现期: 50 年 (风机设计寿命)。

### Business constraints

样本量不足 (少于 10 年数据) 时重现期估计不可靠。
