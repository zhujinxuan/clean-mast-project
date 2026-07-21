## Purpose

Weibull distribution fitting and visualization for wind resource reports.

## Rules

- Pipeline stages: model ← compute ← assemble ← section.
- `compute.py` is pure functions only — no IO, no side effects.
- `assemble.py` is pure — wraps computed data in atoms, no IO.
- Model classes use `frozen=True`.
- WeibullFitter is STATELESS: module-level functions, no class with `__init__`.

## Anti-patterns

- IO in compute or assemble.
- Importing from sibling capabilities.
- Unfrozen model classes.
- `Any`, `# type: ignore`, `str(path)`, bare `except:`.
- Stateful fitter class with config stored in `__init__`.

## When in doubt

- If a calculation is reused by other capabilities → `reporting/compute/`.
- If between compute and assemble: math → compute; wrapping → assemble.

## 业务说明 (Business description)

### Domain context

威布尔分布是风资源评估的基础: 从风速时序数据拟合形状参数 k 和尺度参数 A，得到风速概率密度函数和风能密度曲线。

### Key concepts

WeibullFitter 是无状态模块级函数; k < 2 表示风速变化大 (典型内陆), k > 2 表示风速集中 (典型沿海/海上)。

### Business constraints

拟合方法 (最大似然/最小二乘/矩法) 影响评估结果，默认使用最大似然估计。
