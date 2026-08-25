# cleanmast-dev-tools — spec

Developer tools for the CleanMast workspace. Installed as the `cleanmast-dev`
console script. **Nothing in this package ships to end users.**

## Purpose & principle

Commands whose inputs are **repo fixtures** — `test-data/`, DVC remotes,
Justfiles — live here, never in the `cleanmast` package. A command belongs in
`cleanmast` iff its inputs are user-project artifacts; repo fixtures are
meaningless to an installed end user. (Principle decided 2026-08-25.)

## Commands

- `cleanmast-dev verify` — discover and run test-data datasets via their
  Justfiles (`--package/-p`, `--dry-run`, `--json/-J`, `--jobs/-j`, positional
  `DATASET`).
- `cleanmast-dev baseline` — the six-check gate (ty, ruff, pytest, dvc,
  ast-grep, lint-imports), workspace-wide including typst_ir. Same flags as
  the historical `scripts/verify_baseline.py`, including `--package` and
  repeatable `--skip` with choices `ty|ruff|pytest|dvc|ast-grep|lint-imports`.

## Fixture conventions

A dataset is `test-data/{package}/{dataset}/` containing a `Justfile` with a
`verify-json` recipe. The recipe runs the dataset's verification and prints a
JSON object on stdout:

```json
{
  "name": str,
  "status": "pass" | "fail",
  "duration_sec": number,
  "pull_status": str,
  "pull_duration_sec": number,
  "outputs": list,
  "error": str | null
}
```

Extra keys are tolerated; missing keys are defaulted by the runner.

## Two-mode verify decision (decided 2026-08-25)

Verify is **just-mode only**. The old `verify.toml` `[run]`/`[expect]`
manifest mode was dropped during the migration to this package because every
dataset had already converged on Justfiles. The last stray manifest
(`test-data/cleanmast/kp-202603-report/verify.toml`) was deleted 2026-08-25;
no `verify.toml` is consumed by anything.

## Exit-code contract

`verify` exits 1 on dataset failure **only** in non-json, non-dry-run mode.
In `--json` mode it always exits 0 and reports failures in the JSON summary —
consumers must parse the JSON.

## Naming

Do NOT squat on `doctor` or similar nouns here — `cleanmast doctor` is
reserved for a future user-facing diagnostics command in the main package.

## Dependency rule

This package never imports `cleanmast` internals; it shells out to
executables only (`cleanmast`, `just`, `dvc`), and `cleanmast` must not
depend on it.
