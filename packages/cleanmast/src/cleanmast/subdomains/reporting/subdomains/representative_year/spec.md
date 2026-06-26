## Purpose

Multi-mast representative year calibration summary for wind resource reports.

## Rules

- Pipeline stages: model ← compute ← assemble ← section.
- `compute.py` is pure functions only — no IO, no side effects; receives data as parameters.
- `assemble.py` is pure — wraps computed data in atoms, no IO.
- Model classes use `frozen=True`.

## Anti-patterns

- IO in compute or assemble.
- Importing loaders (`load_timeseries`, `load_representative_year_config`) into compute/section.
- Passing `str(path)` into domain code.
- Importing from sibling capabilities.
- Unfrozen model classes.
- `Any`, `# type: ignore`, `str(path)`, bare `except:`.

## When in doubt

- If a calculation is reused by other capabilities → `reporting/compute/`.
- If between compute and assemble: math → compute; wrapping → assemble.
