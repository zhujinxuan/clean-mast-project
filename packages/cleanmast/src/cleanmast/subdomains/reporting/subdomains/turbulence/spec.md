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
- If a height filter utility is reused → `reporting/compute/`.
- If between compute and assemble: math → compute; wrapping → assemble.
