# E2E Test Criteria: experiment-archive skill

End-to-end acceptance criteria for one full **archive → deploy → runnable**
cycle. Run this after changing `SKILL.md`, `references/deploy.py`, or the
scaffold Justfile. The pass rule is strict: **every check in Phases A and B
must pass; Phase C is required when the change touches deploy.py or the
Justfile.** Any `Warning:` printed by deploy = fail.

Fixture: `evals/2026-07-13-source-experiment/` (or any real project under
`projects/`). Scratch target: `projects/e2e-archive-test` — delete it after
the run.

## Phase A — Archiving produces the correct layout

From a source experiment at `projects/<name>/`:

1. Archive dir created at `experiments-archived/<yyyy-mm-dd>-<name>/`
   (collision suffix `-2`, `-3`, … when needed).
2. **Payload complete**: `parse-sensors.toml`, `masts/`, `mesos/`, `raw/`,
   `pre-masts/` (when present in source), `just-override/` (when present),
   `formats/` (when present).
3. **No generated artifacts**: no `meso-models/`, `reconstruct-*/`,
   `representative-year/`, `rep-ts/`, `investigation/`, `logs/`,
   `process-stats/`, `clean/`, `tower-shading/`, and no generated `*.toml`
   configs (e.g. `process-clean.toml`, `train-meso.toml`).
4. `justfile.archive` is a **byte-identical copy** of the source Justfile:
   `diff projects/<name>/Justfile <archive>/justfile.archive` → empty.
   Any `PROJECT`/`ROOT` rewrite or added recipe = fail.
5. `deploy.py` present at archive root, identical to `references/deploy.py`.
6. Plaintext data dirs compressed one `.tar.zst` per directory, entries
   carrying the directory prefix; every `.tar.zst` and `.parquet` has its own
   `.dvc` sidecar; `dvc status -R <archive>` clean.
7. `.gitignore` allow-lists `!**/justfile.archive` (it is git-tracked, never
   tarred).
8. `ARCHIVE.md` filled with real content (no `<placeholders>`): source, date,
   policy, archive table, parquet table, git-tracked list (incl.
   `justfile.archive`, `deploy.py`, `formats/**`), and Deploy instructions —
   not the old `just pull` flow.
9. `git status <archive>` shows only intended files staged (no `.tar.zst`,
   no `.parquet`, no stray data).

## Phase B — Deploy restores a runnable copy

Run: `uv run python experiments-archived/<archive>/deploy.py projects/e2e-archive-test`

1. Exit code 0; output contains **no `Warning:`** lines.
2. Target root contains: `Justfile` (renamed from `justfile.archive`),
   `parse-sensors.toml`, `masts/`, `mesos/`, `raw/`, `formats/`,
   `just-override/`, `pre-masts/`.
3. **Zero DVC metadata in target** (this is the "not DVC-tracked" contract):
   `glob projects/e2e-archive-test/**/*.dvc` → empty;
   `glob projects/e2e-archive-test/**/*.tar.zst` → empty;
   no `ARCHIVE.md`, no `deploy.py`, no `.gitignore`.
4. **Read-only stripped**: `attrib <target>\raw\*.parquet` shows `A` without
   `R` for every file. (DVC-pulled files are read-only; the pipeline rewrites
   `raw/*.parquet` — a single `R` left behind = fail.)
5. `just -f <target>/Justfile config` prints `Project: projects/e2e-archive-test`
   and the correct repo `Root:` — proves the pristine Justfile works
   unmodified under a new directory name.
6. `just -f <target>/Justfile --list` parses without errors.
7. **Data fidelity**: `diff -r <source>/masts <target>/masts` (and `mesos/`,
   `raw/`, `pre-masts/`) → no differences. Extracted plaintext must land in
   its original location — specifically, `pre-masts/raw/*.txt` must NOT
   appear in top-level `raw/` (nested-extraction regression).
8. Refusal behavior: re-running deploy against the now non-empty target
   exits non-zero with "not empty" unless `--force` is given.

## Phase C — The deployed experiment actually runs

1. **CLI audit**: every `julia bin/CleanMast.jl <module> <cmd>` in the
   deployed Justfile must exist in the current CLI
   (`julia bin/CleanMast.jl <module> --help`). Known-good mapping:
   `recommend process-clean`, `recommend train-reconstruct-cross`,
   `train reconstruct-cross`,
   `recommend reconstruct-cross <train-results.toml> <project-dir>`.
2. Smoke run: `just -f <target>/Justfile recommend-parse-sensors parse-sensors`
   succeeds and regenerates `raw/*.parquet` in the target (proves both the
   read-only strip and `formats/` presence).
3. `formats/sensor/*.toml` paths referenced by `parse-sensors.toml` all exist
   in the target.

## Regression checklist (failure modes this criteria guards against)

| Failure mode | Caught by |
|---|---|
| `justfile.archive` skipped by deploy exclusions → no Justfile in target | B1, B2 |
| `copytree` leaking nested `*.dvc` / `*.tar.zst` | B3 |
| Read-only parquets → `SystemError: Permission denied` on rewrite | B4, C2 |
| Nested `.tar.zst` extracted from wrong cwd (raw txt in top-level `raw/`) | B7 |
| Mutated archived Justfile drifting from original/scaffold | A4, B5 |
| `formats/` missing → parse/clean can't resolve `formats/*` paths | A2, C3 |
| Stale CLI command names (`recommend clean`, `process train-cross`) | C1 |
| Pipeline accidentally run inside `experiments-archived/` (DVC cache risk) | convention: deploy is the only restore path |

## Cleanup

`rm -rf projects/e2e-archive-test` (or the scratch target used).
