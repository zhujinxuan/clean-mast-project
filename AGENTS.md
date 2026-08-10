# CleanMast Project Guide

CleanMast is a comprehensive toolkit for processing wind energy meteorological tower data.

## Default Context

Unless otherwise specified, work refers to **`packages/cleanmast/`**. The Julia package (`CleanMastProject/`) is in maintenance mode; no new features there.

### Terminology

- "Mast" = meteorological tower.
- "Sensor" = a named measurement channel with metadata; never pattern-match raw column strings.
- "Experiment" = a full CleanMast run from preprocessed mast/meso data to report.

### Import conventions

- Python packages import shared IR types from `cleanmast`, not across sibling packages ad hoc.

## Quick Reference

| What | Command |
|------|---------|
| Type check | `uv run ty check packages/cleanmast --output-format full` |
| Lint | `uv run ruff check packages/ --output-format json` |
| Run tests | `uv run pytest packages/cleanmast/tests -q --tb=short -n 4` |
| Run tests (serial) | `uv run pytest packages/cleanmast/tests -q --tb=short` |
| Import contracts | `uv run lint-imports` |
| Test-data verification | `uv run cleanmast verify --json -p cleanmast` |
| Run full baseline | `uv run python scripts/verify_baseline.py --package cleanmast` |
| Load Polars skill | `skill(name="polars")` |

## Standards Docs (spec.md)

Each context and capability has a co-located `spec.md` documenting its conventions and domain notes. These are **standards docs**, not enforced contracts: `/code-review`'s Standards axis reads them; mechanical enforcement lives in `.importlinter` and `.ast-grep/rules/` (run by the baseline).

| When | Load |
|------|------|
| New code in a context | Read `subdomains/spec.md` + the context's `spec.md` |
| Cross-context integration | Read `shared/spec.md` |
| Adding a code rule | Enforcement-first via `skill(name="verify")` — try import-linter/ast-grep before prose |
| Reviewing changes | `/code-review` — Standards axis reads spec.md, skips tool-enforced rules |

## Agent skills

### Issue tracker

Local markdown under `.scratch/<feature>/` (git remote is Gitee; no CLI integration). Drift and known gaps are tickets, never drift-log files. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five canonical labels, recorded as a `Status:` line in each ticket file. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context. `CONTEXT.md` is created lazily by `/grill-with-docs`; historical ADRs are archived read-only under `packages/cleanmast/adr/archived/`; current architecture standards live in the co-located `spec.md` files. See `docs/agents/domain.md`.

## Workspace Structure

```
clean-mast-project/
├── CleanMastProject/     # Julia package (maintenance mode; no new features)
│   ├── src/              # Source code
│   ├── test/             # Test suite
│   └── adr/              # Architecture Decision Records
└── packages/             # Python packages (active development)
    ├── cleanmast/        # Primary development target
    └── preprocess-tools/ # Legacy; being superseded by cleanmast
```

## Development Rules (packages/cleanmast)

### Code quality

- Always specify `encoding="utf-8"` when reading/writing text files. Windows defaults to `gbk`/`cp1252`, which causes `UnicodeDecodeError` on JSON, typst source, and log files.
- Use Pydantic `BaseModel` for all IR types.
- Use `pathlib.Path` for all file operations.
- Prefer domain-specific types over primitive strings/ints.
- No bare `Any` unless the boundary genuinely cannot be typed.

### Justfiles

- All Justfiles use nushell: `set shell := ["nu", "-c"]`. Never `cmd`.
- Recipes must be nushell syntax — no cmd idioms (`&&`, `if exist`, `rmdir /s /q`, `start`, `2>nul`, `%VAR%`). Use `;` sequencing, `path exists`, `rm -rf`, `try { … } catch { … }`.
- No naked `python` in recipes; always `uv run python`.

### Imports

- Import shared IR types from `cleanmast`, not from sibling packages.
- Never create circular imports between subdomains; use `shared/` for cross-subdomain contracts.
- Run `uv run lint-imports` before committing to verify DDD contracts.

### Architecture

- Read the relevant `spec.md` before coding in a context.
- New code lives in the appropriate subdomain under `packages/cleanmast/src/cleanmast/subdomains/`.
- Cross-context integration uses `packages/cleanmast/src/cleanmast/shared/`.

## Consistency Gate

Between waves or before final delivery, run a multi-dimensional consistency gate. A gate must check at least two dimensions in parallel.

### Minimum gate (always)

1. **Logical consistency** — tests pass, imports resolve, public API contracts hold.
2. **Spec consistency** — directory layout and dependency direction match the relevant `spec.md`.

### Add when risk warrants

3. **Structural hygiene** — no one-line shim files, no bare `Any`, no dead exports.
4. **Code taste consistency** — naming, error handling, and abstraction level match the codebase.
5. **Scope fidelity** — no cross-task contamination or unaccounted changes.

Use parallel subagents for each dimension. The gate passes only when all subagents pass.

## packages/cleanmast

### Verification

Run after every implementation task, before committing:

```bash
uv run python scripts/verify_baseline.py --package cleanmast
```

Six checks: **ty**, **ruff**, **pytest**, **dvc-verify**, **ast-grep**, **lint-imports** — all blocking. Skill: `skill(name="verify")`. Every implementation ticket's acceptance criteria end with this command green.

**Output:** Per-package baseline files at `packages/cleanmast/baseline-{timestamp}.md`
- Small errors (<500 chars): Inline in markdown
- Large errors (≥500 chars): Written to `baseline-refs/{timestamp}-{tool}.json`

