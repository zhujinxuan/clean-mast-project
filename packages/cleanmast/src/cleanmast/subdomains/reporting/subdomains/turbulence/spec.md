## Purpose

Single-mast turbulence intensity analysis for wind resource reports.

## Rules

- Pipeline stages: model ← compute ← assemble ← section.
- `compute.py` is pure functions only — no IO, no side effects.
- `assemble.py` is pure — wraps computed data in atoms, no IO.
- Model classes use `frozen=True`.
- No stateful calculators; all state passed as explicit parameters.
- IEC categories are module-level constants (not mutable instance state).

## Anti-patterns

- IO in compute or assemble.
- Importing from sibling capabilities.
- Unfrozen model classes.
- `Any`, `# type: ignore`, `str(path)`, bare `except:`.
- Stateful class with mutable `self.iec_categories` dict.

## When in doubt

- If a calculation is reused by other capabilities → `reporting/compute/`.
- If between compute and assemble: math → compute; wrapping → assemble.

## 业务说明 (Business description)

### Domain context

湍流强度 TI = σ / v_mean，是风机疲劳载荷评估的关键参数。按 IEC 61400-1 标准分级: A 类 (高湍流)、B 类 (中湍流)、C 类 (低湍流)。

### Key concepts

IEC 类别是模块级常量; TI 按风速 bin 分段计算 (bin-by-bin)，典型 bin 宽度 1 m/s。

### Business constraints

IEC 标准定义了 TI 参考曲线 (TI_ref = I_ref * (0.75 + 5.6/v))，实际 TI 必须低于参考曲线对应的类别阈值。
