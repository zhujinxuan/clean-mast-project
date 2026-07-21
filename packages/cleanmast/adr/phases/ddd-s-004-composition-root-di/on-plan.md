# Handoff: Composition Root + DI (ddd-s-004) — Design & Execution Plan

Audience: whoever picks this up later (human or agent). Read the main ADR first
(`../../2026-07-19-composition-root-di.md`). Everything below is evidence-backed as of
2026-07-19; commit at writing: `79fc2ace`.

## 1. Context — why this exists

The package `.importlinter` has 8 contracts, all now parseable; 6 KEPT, 2 BROKEN:

| Contract | Status | Residual |
|---|---|---|
| `subdomain-isolation` (independence: dataprocessing, configuration) | BROKEN | ONE edge: `configuration/services/recommend_fill_heights.py:19` → `dataprocessing/services/height_filling/planner.py` (`generate_dual_configs`) |
| `cli-isolation` (forbidden: cli → dataprocessing, cli → db.repositories) | BROKEN | 3 transitive chains through `application` (below) |

The 3 cli-isolation chains (verified):
```
cli → adapters.cli.generate_wt_timeseries → application.usecases.generate_wt_timeseries → dataprocessing.services.wt_timeseries_generator
cli → adapters.cli.execute_fill_heights   → application.usecases.execute_fill_heights   → dataprocessing.services.height_filler
cli → adapters.cli.recommend_fill_heights → configuration.services.recommend_fill_heights → dataprocessing...height_filling.planner
```

These chains are *legitimate composition-root paths* — the contract fights the
intended architecture. The author's dead `allowed_modules = cleanmast.application`
(a no-op field on `type=forbidden`, verified against import-linter 2.13 source:
only `protected` contracts have `allowed_importers`) proves the intent was to allow
the application path but it was never expressed correctly.

Historical continuity: archived ADR `ddd-s-002-context-maps` prescribed exactly this
(protocol in shared, DI in `bootstrap.py`) and was never implemented; the abandoned
`TimeSeriesRepository` protocol drifted unused until Wave B (2026-07-19) revived the
pattern at `shared/timeseries/io/repository.py` — use it as the in-repo precedent.

Ground already prepared (waves 0–C, commits `8948cbb8`..`d3170916`): all timeseries IR
+ IO canonical in `shared/timeseries{,/io}`; `dataingestion` deleted; every CLI command
already flows cli → adapters → application → subdomain service (the shape this ADR
formalizes with protocols).

## 2. Principles

1. **Protocol association between domains; implementation association nowhere.**
   Cross-domain capabilities are exposed as `Protocol`s in `shared/` (or a
   `shared/protocols/` package if the count grows past ~3).
2. **One composition root.** `cleanmast/bootstrap.py` is the ONLY module importing
   concrete cross-domain implementations; it builds usecases via factory functions.
3. **Thin CLI.** `cli.py` / `adapters/cli/*` parse args, call `bootstrap.build_*()`,
   invoke the usecase. No direct submodule imports.
4. **Contracts match the architecture.** `cli-isolation` uses
   `allow_indirect_imports = true`: direct imports policed, transitive reach through
   bootstrap sanctioned. Never paper over with `ignore_imports` lists.
5. **Repo hygiene rules stay:** no shims/aliases; frozen pydantic for config types;
   `encoding="utf-8"`; behavior-preserving waves (golden gate proves it).
6. **Recommend-phase review workflow preserved:** fitted shear/deg-diff values still
   materialize in the fill-heights TOML at recommend time; only the call site moves.

## 3. Spec / config updates this ADR requires

| File | Change |
|---|---|
| `packages/cleanmast/.importlinter` → `cli-isolation` | add `allow_indirect_imports = true`; keep `forbidden_modules = dataprocessing, cleanmast.db.repositories` (direct-import guard) |
| `packages/cleanmast/.importlinter` → `subdomain-isolation` | goes KEPT once wave 2 lands (no text change needed) |
| `subdomains/spec.md` | new rule: cross-context services are exposed as protocols in shared; composition root is `cleanmast/bootstrap.py`; cli/adapters may not import subdomains directly |
| `scripts/verify_baseline.py` | after all-KEPT: add a package-config lint-imports run alongside the root one (currently root only) |
| `AGENTS.md` (Quick Reference) | add bootstrap note once landed |

## 4. Wave plan

**Wave 1 — protocols + builders.** Define `FillPlanner` and
`WtTimeseriesGenerator` protocols (source-shaped, mirroring current call signatures:
`generate_dual_configs(...)`, `process_wt_timeseries(config, project_dir)`, planner's
fit entry). Dataprocessing realizations conform structurally (no base-class coupling;
`Protocol` + structural typing). Verify: scoped pytest + ty.

**Wave 2 — usecase injection + recommend orchestration move (fixes #2).**
`application/usecases/*` take protocols via constructor kwargs (default arg = None is
FORBIDDEN — explicit injection). Move the `recommend_fill_heights` orchestration
(discover configs → build `MastPlanningEntry` lists → call planner) from
`configuration/services/recommend_fill_heights.py` into an application usecase;
the configuration service returns discovered configs only. Verify:
`subdomain-isolation` KEPT in a temp sweep.

**Wave 3 — bootstrap + cli rewiring.** `cleanmast/bootstrap.py`: factory functions
`build_fill_planner()`, `build_wt_timeseries_generator()`, `build_*_usecase()`.
cli.py/adapters call bootstrap; delete their direct subdomain imports. Verify:
`uv run lint-imports` green incl. new `allow_indirect_imports`.

**Wave 4 — contract + spec updates + full gate.** Apply §3 edits; baseline 6/6;
golden pipeline diff (§5); commit per wave.

## 5. How to ensure (verification gate)

1. **Baseline per wave**: `uv run python scripts/verify_baseline.py --package cleanmast`
   (ty, ruff, pytest, dvc-verify, lint-imports, ast-grep) — must be 6/6.
2. **Golden pipeline diff** (the behavior proof): `projects/2026-07-02-松原-gate/`
   is the standing regression master (original `projects/2026-07-02-松原/` untouched
   = pre-refactor golden). Run the Python tail
   `just -f projects/2026-07-02-松原-gate/Justfile recommend-fill-heights fill-heights-meso fill-heights-representative-year recommend-wt-timeseries process-wt-timeseries recommend-report-config report-timeseries`
   then hash-diff vs the original. Expected-diff ledger (from 2026-07-19 calibration):
   repyear fill values differ (stale golden fits — input vintage July-2 15:23),
   `extreme_wind_*` TOML fields added, `repyear/M3142` air_density 1.225→1.242,
   unseeded Gumbel Monte Carlo pixels. Everything else must be byte-identical.
   Every rewired CLI command is exercised by this tail.
3. **Contract sweeps**: root (5) + package (8) both fully KEPT at the end — that is
   the acceptance criterion of this ADR.
4. **Characterization net**: the 65-test data-loading suite +
   `tests/subdomains/dataprocessing` planner tests stay green; add a cli smoke test
   per rewired command (invoke `--help` path or dry entry — no mocks).

## 6. Open questions (decide at kickoff)

- Protocol granularity: one protocol per usecase (recommended — matches how CLI
  commands map) vs per domain service (finer, more wiring).
- Keep `adapters/cli/*` as thin per-command modules, or collapse to a single
  dispatch in `cli.py` + bootstrap?
- `recommend` orchestration for OTHER commands (report-configs, wt-timeseries):
  same injection treatment, or only fill-heights for now?
- Problem-2 future work (user note 2026-07-19): "recommend is NOT purely
  non-computational" — consider a dedicated home for recommend-phase
  computation + selection logic (which heights to choose) outside configuration.
  This ADR's application-usecase move is compatible as an interim step.

## 7. Known traps (from the 2026-07-19 waves)

- Agents claiming lint/type errors are "pre-existing" — on a green baseline they
  are regressions; verify against the last green baseline before accepting.
- Multi-file renames: run `grep` for the OLD name across src+tests+configs
  (`.importlinter`, both files) before declaring zero references.
- `unmatched_ignore_imports_alerting = error` (default): stale ignore entries
  become errors the moment an edge disappears — prune them in the same commit.
