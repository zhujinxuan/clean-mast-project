## Purpose

Single-mast wind temporal pattern analysis for wind resource reports.

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

风速/风向的日变化和月变化模式分析，反映站点的大气边界层特征。

### Key concepts

日变化按小时 (0–23) 聚合；月变化按日历月聚合。
