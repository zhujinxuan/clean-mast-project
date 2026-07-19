# Session Prompt — paste into a new agent session

```text
Execute ADR ddd-s-004-composition-root-di in packages/cleanmast (CleanMast workspace).

Read first, in order:
1. packages/cleanmast/adr/ddd-s-004-composition-root-di.md (the decision)
2. packages/cleanmast/adr/phases/ddd-s-004-composition-root-di/on-plan.md (handoff:
   evidence, principles, spec updates, 4-wave plan, verification gate, open questions, traps)
3. todos/2026-07-19-ddd-s-004-execution/kickoff-decisions.md (pre-settled + pending
   forks, FULL cross-domain edge inventory — supersedes the handoff's partial list)
4. packages/cleanmast/src/cleanmast/subdomains/spec.md + shared/timeseries/spec.md
5. The working precedent: shared/timeseries/io/repository.py + file_repository.py

Step 0 (before any planning): run
`uv run lint-imports --config packages/cleanmast/.importlinter`
and confirm the on-plan.md §1 truth table still holds (6 KEPT; subdomain-isolation +
cli-isolation BROKEN with the exact residuals listed). If reality differs, stop and
report — do not plan on stale evidence.

Pre-settled (user decision 2026-07-19, do not re-litigate):
- Uniform injection is ABSOLUTE: "implementation association nowhere" has no
  pure-function exemption. height_filler (apply_ws_fill / apply_wd_fill) gets a
  protocol like planner and wt_timeseries_generator; bootstrap passes the module
  itself (structural conformance, no wrapper class).
- Fix the `_validate_references` private-name cross-context import as part of the
  wave (make public or fold into the filler's public API).

Kickoff — resolve with me BEFORE starting wave 1:
1. SCOPE OF UNIFORMITY (the big one, see kickoff-decisions.md §Fork 2): the full
   grep inventory includes turbulence_calculator and the reporting service surface
   (ReportGenerationService, build_section_tree, models) plus configuration
   load_config / ProjectConfig / FlatReportConfig — none named in the handoff.
   Options: full inventory (~6 waves, config types → shared per the timeseries
   migration precedent) / named chains only (defer turbulence + reporting to a
   follow-up ADR) / contract-minimal. Agent proposes with one-line rationale.
2. Protocol granularity: one per usecase (handoff recommendation) vs per domain service.
3. adapters/cli shape: thin per-command modules vs single dispatch in cli.py + bootstrap.
4. Recommend orchestration for OTHER commands (report-configs, wt-timeseries):
   same injection treatment, or fill-heights only for now.
5. Problem-2 interim fit (on-plan.md §6): the application-usecase move is an
   interim step toward a dedicated home for recommend-phase computation — confirm
   the wave plan stays compatible.

Working agreements:
- One wave per commit. Each wave ends with
  `uv run python scripts/verify_baseline.py --package cleanmast` at 6/6 green
  BEFORE committing.
- No shims, aliases, re-export facades, or default-argument injection — explicit
  constructor injection only.
- After any multi-file rename, grep the old name across src + tests + BOTH
  .importlinter files before declaring zero references.
  unmatched_ignore_imports_alerting=error: stale ignore entries become errors the
  moment an edge disappears — prune them in the same commit.
- Lint/type errors on a green baseline are regressions until proven otherwise —
  verify against the last green baseline before claiming "pre-existing".
- Delegate multi-file work to subagents; run the gates yourself.
- Golden gate needs local untracked dirs projects/2026-07-02-松原{,-gate};
  if missing, recreate the gate copy before starting.

Acceptance (all required):
- `uv run lint-imports` (root config): 5/5 KEPT.
- Package sweep (packages/cleanmast/.importlinter): all 8 contracts parse, ALL
  KEPT — cli-isolation via allow_indirect_imports=true, subdomain-isolation via
  the orchestration move to application.
- Golden pipeline diff per on-plan.md §5:
  `just -f projects/2026-07-02-松原-gate/Justfile recommend-fill-heights
  fill-heights-meso fill-heights-representative-year recommend-wt-timeseries
  process-wt-timeseries recommend-report-config report-timeseries`
  then hash-diff against the untouched original projects/2026-07-02-松原/.
  Differences limited to the §5 expected-diff ledger (stale-golden repyear fits,
  extreme_wind_* TOML fields, M3142 air_density 1.225→1.242, unseeded Gumbel MC
  pixels); everything else byte-identical.
- cli smoke test per rewired command (no mocks); the 65-test data-loading suite
  and dataprocessing planner tests stay green.
- Package lint-imports config wired into scripts/verify_baseline.py as a
  permanent gate once all-KEPT.
```
