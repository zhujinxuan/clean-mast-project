## Purpose

Vertical wind profile and shear analysis for single-mast reports.

## Rules

- Pipeline stages: model ← compute ← assemble ← section.
- `compute.py` is pure functions only — no IO, no side effects.
- `assemble.py` is pure — wraps computed results in atoms, no IO.
- Model classes use `frozen=True`.

## Anti-patterns

- IO in compute or assemble.
- Importing from sibling capabilities.
- Unfrozen model classes.
- `Any`, `# type: ignore`, `str(path)`, bare `except:`.

## When in doubt

- If a calculation is reused by other capabilities → `reporting/compute/`.
- If between compute and assemble: math → compute; wrapping → assemble.

## 业务说明 (Business description)

### Domain context

垂直风廓线描述风速随高度的变化，遵循幂律 (power law): v₂/v₁ = (h₂/h₁)^α，其中 α 是风切变指数。

### Key concepts

风切变指数 α 是站点物理属性，典型值 0.1–0.4。

### Business constraints

风廓线直接影响风机扫掠面的载荷分布，但载荷模拟需要叶片几何、控制策略等设备商机密数据 — 本系统仅计算风廓线本身，不涉入风机响应仿真。
