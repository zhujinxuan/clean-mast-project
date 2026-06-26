## Purpose

Wind rose frequency distribution (16-sector polar) computation and chart rendering for wind resource reports.

## Rules

- Pipeline stages: model ← compute ← assemble ← section.
- `compute.py` is pure functions only — no IO, no side effects.
- `assemble.py` is pure — wraps computed data in atoms, no IO.
- Model classes use `frozen=True`.
- No hardcoded angles (22.5, 16); use named constant `SECTOR_COUNT` and derive sector width.

## Anti-patterns

- IO in compute or assemble.
- Importing from sibling capabilities.
- Unfrozen model classes.
- `Any`, `# type: ignore`, `str(path)`, bare `except:`.
- Hardcoded magic numbers (22.5, 16).
- `rows: list[dict]` in assemble; use typed structures.

## When in doubt

- If a calculation is reused by other capabilities → `reporting/compute/`.
- If between compute and assemble: math → compute; wrapping → assemble.
