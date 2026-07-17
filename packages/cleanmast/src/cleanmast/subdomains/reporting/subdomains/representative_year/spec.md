## Purpose

Multi-mast representative year calibration analysis for wind resource reports. Produces a summary table (all masts), per-mast 16-sector statistics table, and per-mast 4×4 Altair scatter grid.

## Rules

- Pipeline stages: model ← compute ← assemble ← section.
- `compute.py` is pure functions only — no IO, no side effects; receives data as parameters.
- `assemble.py` is pure — wraps computed data in atoms, no IO.
- Model classes use `frozen=True`.
- `section.from_inputs` accepts `list[SingleMastAnalysisInput]` with calibration payloads.
- Per-mast figures use Altair for 4×4 sector scatter grids.

## Anti-patterns

- IO in compute or assemble.
- Importing loaders (`load_timeseries`) into compute/section.
- Passing `str(path)` into domain code.
- Importing from sibling capabilities.
- Unfrozen model classes.
- `Any`, `# type: ignore`, `str(path)`, bare `except:`.

## When in doubt

- If a calculation is reused by other capabilities → `reporting/compute/`.
- If between compute and assemble: math → compute; wrapping → assemble.
