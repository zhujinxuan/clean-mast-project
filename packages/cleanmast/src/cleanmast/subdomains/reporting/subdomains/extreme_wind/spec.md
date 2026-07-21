## Purpose

Fifty-year max wind (extreme wind) analysis for wind resource reports. Covers IEC 61400-1 Methods 1/2/3, Gumbel distribution fitting, and IEC wind class classification.

## Rules

- Pipeline stages: model ← compute ← assemble ← section.
- `compute/` is pure functions only — no IO, no side effects.
- `assemble/` is pure — wraps computed data in atoms, no IO.
- Model classes use `frozen=True`.
- `renderImage()` returns `Path()` for no-image (compatible with base class), not `None`.

## Anti-patterns

- IO in compute or assemble.
- Importing from sibling capabilities.
- Unfrozen model classes.
- `Any`, `# type: ignore`, `str(path)`, bare `except:`.
- `Path()` sentinel replaced — Q-Q subgrid functions use proper altair types.

## When in doubt

- If a calculation is reused by other capabilities → `reporting/compute/`.
- If between compute and assemble: math → compute; wrapping → assemble.
- IEC standards table is not mast-specific → assembled as NoMast atom.

## 业务说明 (Business description)

### Domain context

极端风速分析预测 N 年重现期的最大风速，使用 Gumbel 极值分布拟合年最大值序列。

### Key concepts

典型重现期: 50 年 (风机设计寿命)。

### Business constraints

样本量不足 (少于 10 年数据) 时重现期估计不可靠。
