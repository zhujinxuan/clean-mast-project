---
name: verify
description: Run the CleanMast verification baseline (ty, ruff, pytest, dvc-verify, lint-imports, ast-grep) and interpret failures. Use after an implementation task, before committing, when a baseline check fails, or when a new code rule should be enforced mechanically.
---

# Verify

One command:

```bash
uv run python scripts/verify_baseline.py --package cleanmast
```

Six checks, in order: **ty** (types), **ruff** (lint), **pytest**, **dvc-verify** (test data), **lint-imports** (import contracts), **ast-grep** (custom structural rules in `.ast-grep/rules/`).

Blocking: ty, ruff, pytest, dvc-verify, ast-grep. Advisory: lint-imports — failures are reported but do not fail the run.

Output: `packages/cleanmast/baseline-{timestamp}.md`. Small errors inline; large ones in `packages/cleanmast/baseline-refs/{timestamp}-{tool}.json`.

## Individual checks

| Check | Command |
|-------|---------|
| ty | `uv run ty check packages/cleanmast --output-format full` |
| ruff | `uv run ruff check packages/ --output-format json` |
| pytest | `uv run pytest packages/cleanmast/tests -q --tb=short -n 4` |
| pytest (serial) | `uv run pytest packages/cleanmast/tests -q --tb=short` |
| lint-imports | `uv run lint-imports` |
| ast-grep | `uv run ast-grep scan --config .ast-grep/sgconfig.yml packages/cleanmast/src/cleanmast/` |

## Adding a new code rule — enforcement-first

When a new convention is agreed (in a ticket, a review, or a `spec.md` edit), try mechanical enforcement before leaving it to review judgment:

1. **Import direction?** Add or extend a contract in `.importlinter`, then run `uv run lint-imports`.
2. **Code shape?** Write an ast-grep rule in `.ast-grep/rules/<id>.yml`. Prove it before merging: introduce a deliberate violation, confirm `ast-grep scan` fires on it; revert, confirm it stays silent on compliant code.
3. **Neither fits?** Leave it as prose in the relevant context's `spec.md` — `/code-review`'s Standards axis judges it there.

Mechanical beats prose: a rule a tool checks never gets re-litigated in review.
