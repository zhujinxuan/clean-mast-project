# 01 — Migrate verify command to cleanmast-dev-tools package

**What to build:** Move the `cleanmast verify` command out of the `cleanmast` package into a new `packages/cleanmast-dev-tools` package. Principle (decided 2026-08-25): **dev-driven commands never ship in the cleanmast package** — a command belongs in `cleanmast` iff its inputs are user-project artifacts; `verify` consumes repo fixtures (`test-data/`, DVC remotes, Justfiles), which are meaningless to an installed end user.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Scope

- New workspace member `packages/cleanmast-dev-tools` (follow the existing two-package layout; near-zero dependencies — `verify.py` shells out to `cleanmast`/`just`/`dvc` and imports no cleanmast internals).
- Move `packages/cleanmast/src/cleanmast/interfaces/cli/verify.py` and its tests into the new package; expose a console script (recommend `cleanmast-dev verify`, keeping the same flags: `--package`, `--json`, `--dry-run`, `-j`, dataset arg).
- Remove `main.add_command(verify, "verify")` from `cleanmast/interfaces/cli/main.py`.
- Repoint the dvc-verify step in `scripts/verify_baseline.py` (`uv run cleanmast verify --json -p cleanmast` → new entry point).
- Update workspace `pyproject.toml` members and the AGENTS.md quick-reference row for test-data verification.
- Move the baseline implementation from `scripts/verify_baseline.py` into the new package (`cleanmast-dev baseline`); reduce `scripts/verify_baseline.py` to a thin wrapper delegating to it (see decision below).

## Doc placement (decided 2026-08-25)

| Document | Location |
|---|---|
| New package's spec | `packages/<new-pkg>/spec.md` — commands, fixture conventions, the two-mode verify decision |
| The dev-driven-command principle | AGENTS.md development rules (auto-loaded every session) |
| Command changes | AGENTS.md quick-reference table |
| `cleanmast doctor` reservation | one line in AGENTS.md so the noun isn't squatted |

`docs/agents/issue-tracker.md:20`, the `lint_tickets.py` acceptance-string check, AGENTS.md's baseline command, the verify skill, and `packages/typst_ir/README.md` are all **untouched**: see the baseline-wrapper decision below.

## Baseline runner: functionality moves, path stays (decided 2026-08-25)

The six-check baseline implementation moves from `scripts/verify_baseline.py` into the dev-tools package as a proper module (e.g. `cleanmast_dev_tools/baseline.py`) with a console script (`cleanmast-dev baseline --package cleanmast`, same flags including `--skip`). `scripts/verify_baseline.py` becomes a **thin wrapper** delegating to it — the command string every ticket, hook, skill, and doc references keeps working unchanged. The dev-tools package thus ships two commands: `verify` (test-data datasets) and `baseline` (six-check gate, workspace-wide incl. typst_ir).

## Enforcement: dev commands stay out of cleanmast (three layers)

1. **AGENTS.md rule** (procedural, auto-loaded): dev-driven commands (inputs = repo fixtures: test-data/, DVC, Justfiles) live in the dev package; the `cleanmast` CLI only takes user-project inputs.
2. **One ast-grep rule** in `.ast-grep/rules/`: ban `test-data` / DVC-fixture coupling inside `packages/cleanmast/src` — the actual signature of dev-driven code; fires in the existing baseline ast-grep check.
3. **Dependency direction**: `cleanmast` must not depend on the dev package — one import-linter forbidden contract in `.importlinter`, plus simply not declaring the dependency.

## Resolve during implementation

- **Two-mode divergence:** today's verify has a just-mode (`just verify-json`, used under `--json`) and a manifest mode (`verify.toml` `[run]`/`[expect]`), and they behave differently — just-mode regenerates report configs via recommend, manifest mode consumes the committed config. Pick one mode during the migration (recommend: just-mode only, manifest becomes documentation) or keep both deliberately; either way, document the choice in the ticket resolution.
- **`cleanmast doctor` name reservation:** do NOT squat on `doctor` or similar nouns in the dev-tools package. `cleanmast doctor` is reserved for a future user-facing diagnostics command in the main package: dataset/parquet existence, config-referenced sensors exist with required stat types, metadata sanity, common config problems.

## Acceptance

- [ ] `cleanmast verify` no longer exists; `cleanmast-dev verify` (or chosen name) runs the same discovery/execution
- [ ] Baseline dvc-verify step green via the new entry point
- [ ] No dev-fixture-consuming code remains in the cleanmast wheel surface
- [ ] Baseline implementation lives in the dev package (`cleanmast-dev baseline`); `scripts/verify_baseline.py` is a thin wrapper and the old command string still works
- [ ] Doc placement done per the table above (new package spec.md, AGENTS.md principle + quick-reference, doctor reservation)
- [ ] Enforcement layers 1–3 in place: AGENTS.md rule, ast-grep rule banning test-data/DVC-fixture coupling in `packages/cleanmast/src`, import-linter forbidden contract cleanmast ↛ dev package
- [ ] Two-mode divergence resolved and documented in the new package's spec.md
- [ ] Tests moved/updated with the command
- [ ] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- Decided 2026-08-25: user sets the principle that dev-driven code stays out of the cleanmast package; `scripts/verify_baseline.py` already lives at repo root and stays.
- Future `cleanmast doctor` checks (user-listed): sensors exist, metainformation, common problems, dataset exists or not.
