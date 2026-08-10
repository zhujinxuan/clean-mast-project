# 05 — Deepen application/spec.md for config-driven usecases

**What to build:** Make `application/spec.md` able to steer the usecase layer: 3 of 5 real usecases (recommend/train/execute fill-heights) are config-driven, yet the spec says nothing about ProjectConfig, config discovery, persistence, or repository injection. Also absorb the train-workflow orchestration pattern that currently lives (misplaced) in subdomains/spec.md. File: `packages/cleanmast/src/cleanmast/application/spec.md` (+ removal in subdomains/spec.md). Details in `.scratch/spec-docs-cleanup/findings.md`.

**Blocked by:** None — 02-hub-specs-fix done 2026-08-10 (commit 7b933e25)

**Status:** done

- [x] Move the train-workflow orchestration pattern from subdomains/spec.md (rule 11) into application/spec.md; subdomains keeps a one-line pointer
- [x] Add config-driven usecase rules: ProjectConfig loading (`discover_*_config()` vs `load_config()`), model persistence (`save_*_model()`), repository injected by `cleanmast.bootstrap`
- [x] Reduce the TimeSeriesData-boundary restatement to a pointer (dataprocessing/spec.md owns the enforceable side)
- [x] Drop the `## Code rules` wrapper → flat 5-section format, and add a 业务说明 section (the only spec without one)
- [x] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- From the 2026-08-10 spec-docs review. Full quotes in `../findings.md`.
- Resolved 2026-08-10: application/spec.md rewritten — flat 5-section format, config-driven usecase rules (ProjectConfig discover/load_config/save_*_model, bootstrap injection), train-workflow pattern absorbed from subdomains/spec.md rule 11 (now a pointer there), TimeSeriesData boundary reduced to a pointer at dataprocessing/spec.md, 业务说明 added.
