# Kickoff Decisions — ddd-s-004 Grill Record (2026-07-19)

## Layer roles (agreed vocabulary)

```
cli.py + adapters/cli/*   trigger. Parses argv, calls bootstrap.build_*(), invokes
                          the usecase. Knows nothing about subdomains.
bootstrap.py  (new)       assembly. The ONLY module importing concrete subdomain
                          implementations; wires them into usecases.
application/usecases/*    procedure. Ordered steps of ONE user operation:
                          load config → load data → invoke capabilities → save.
                          Owns step ORDER; zero domain math; zero concrete imports.
subdomains/*              knowledge. configuration = what user asked for;
                          dataprocessing = the math; reporting = the document.
shared/                   lingua franca. IR types + protocols + io.
```

## Mechanism recap (why the fork existed)

Two-phase fill-heights flow:

```
Phase 1 — recommend (training)          Phase 2 — execute (usecase)
planner fits shear / deg_diff           load fill-heights-*.toml
from measured data        ──writes──>   per mast, per target height:
into fill-heights-*.toml    TOML          apply_ws_fill(df, refs, shear)
(human reviews/edits TOML)                apply_wd_fill(df, refs, deg_diff)
                                        append columns → save parquet
```

User's key observation: execute uses config **including trained results** — shear /
deg_diff arrive as plain numbers (data); the usecase trains nothing. `apply_ws_fill`
is pure math over trained params. This motivated the exemption question — resolved
below toward uniformity anyway.

## Fork 1 — height_filler protocol? → SETTLED: uniform injection

Decision (user, 2026-07-19): **"implementation association nowhere" is absolute.**
- HeightFiller protocol in shared (apply_ws_fill / apply_wd_fill / validate_references).
- bootstrap passes the `height_filler` module itself — structural Protocol
  conformance, no wrapper class, ~15-line protocol file.
- Fix `_validate_references` (private name imported cross-context from
  `dataprocessing/services/height_filling/validation.py` into
  `application/usecases/execute_fill_heights.py`) — make public or fold into the
  filler's public API.
- Rationale rejected: "pure functions are exempt" — exemption rules get re-litigated
  per import, and NO contract polices application→subdomain edges, so drift would be
  invisible.

## Fork 2 — scope of uniformity → PENDING (the kickoff blocker)

Grep evidence (2026-07-19, `from cleanmast.subdomains` in application/ + adapters/,
23 matches in 6 files) shows the handoff's protocol list is incomplete:

| Edge | Handoff named it? |
|---|---|
| application → dataprocessing: planner, wt_timeseries_generator | yes (2 protocols) |
| application → dataprocessing: height_filler, validation | Fork 1 — inject |
| application → dataprocessing: **turbulence_calculator** (generate_wt_timeseries usecase) | **no** |
| application → reporting: **ReportGenerationService, build_section_tree, analysis_input models + more** (generate_report usecase, 10 matches) | **no** |
| application/adapters → configuration: load_config, ProjectConfig, FlatReportConfig, recommend_* services | **no** |

Options:
1. **Full inventory** (agent recommendation): protocols for all behavior edges;
   config types + load_config migrate to shared/ per the timeseries-migration
   precedent (types move, behavior gets protocols). Wave plan grows 4→~6 waves,
   grouped by usecase family (fill-heights first — golden gate covers it).
   One architecture, no leftover exceptions.
2. Named chains only: this ADR covers the 3 cli-isolation chains + height_filler +
   recommend services; turbulence + reporting deferred to a follow-up ADR with an
   explicit note. Risk: two classes of usecases coexist; the unfinished half
   invites new direct imports by example.
3. Contract-minimal: allow_indirect_imports fixes cli-isolation with NO new
   protocols; only the recommend→planner move for subdomain-isolation. Principle 1
   becomes mostly aspirational. Rejected by the spirit of Fork 1 but listed for
   completeness.

## Still-open handoff §6 questions (to settle at kickoff with Fork 2)

1. Protocol granularity: one per usecase (handoff recommendation) vs per domain service.
2. adapters/cli shape: thin per-command modules vs single dispatch in cli.py + bootstrap.
3. Recommend orchestration for OTHER commands (report-configs, wt-timeseries):
   same injection treatment or fill-heights only.
4. Problem-2 interim fit: "recommend is NOT purely non-computational" (user note
   2026-07-19) — the application-usecase move is interim toward a dedicated home for
   recommend-phase computation + selection logic outside configuration.

## Environment notes

- Golden gate dirs `projects/2026-07-02-松原/` (untouched master) and
  `projects/2026-07-02-松原-gate/` (working copy, 1.8GB) are local-only, untracked.
- Handoff evidence stamped at commit 79fc2ace; HEAD at discussion time was
  4bdd2506 (handoff doc commit only — tree expected to match; Step 0 verifies).
- Expected-diff ledger for the golden gate lives in on-plan.md §5 item 2
  (there is no §5.2 — earlier drafts referenced it wrong).
