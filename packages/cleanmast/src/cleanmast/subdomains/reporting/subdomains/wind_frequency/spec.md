## Purpose

Single-mast wind speed frequency distribution analysis for wind resource reports.

## Rules

- Pipeline stages: model ← compute ← assemble ← section.
- `compute.py` is pure functions only — no IO, no side effects, no stateful classes.
- `assemble.py` is pure — wraps computed DataFrames in atoms, no IO.
- Model classes use `frozen=True`.
- Wind frequency computation uses vectorized Polars operations; no intermediate `rows: list[dict]` accumulation.

## Anti-patterns

- Stateful calculator classes.
- IO in compute or assemble.
- Importing from sibling capabilities.
- Unfrozen model classes.
- `Any`, `# type: ignore`, `str(path)`, bare `except:`.
- Building DataFrames from `list[dict]` in compute.

## When in doubt

- If a calculation is reused by other capabilities → `reporting/compute/`.
- If between compute and assemble: math → compute; wrapping → assemble.

## 业务说明 (Business description)

### Domain context

风速频率分布直方图，按指定 bin 宽度统计各风速段的出现频率。

### Key concepts

bin 宽度默认 1 m/s；频率可表示为绝对频次或百分比。
