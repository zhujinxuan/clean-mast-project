## Purpose

Multi-mast air density calculation for wind resource reports.

## Rules

- Pipeline stages: model ← compute ← assemble ← section.
- `compute.py` is pure functions only — no IO, no side effects.
- `assemble.py` is pure — wraps computed data in atoms, no IO.
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

空气密度影响风功率计算: P = 0.5 ρ A v³。密度由温度、气压、海拔决定 (理想气体定律)。

### Key concepts

标准空气密度 1.225 kg/m³ (15°C, 海平面)；实际密度因站点海拔和季节变化偏离标准值。
