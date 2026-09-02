# 11 — Reference-height selection (O(n²) kill)

**Type:** grilling

**Status:** resolved

**Blocked by:** None

## Question

Finalize the O(n²) kill: selection-stage screening runs at reference height only; the winner gets a full-height final fit.

Decide:

1. **Reference height choice**: per-mast highest WS vs configured (e.g. 160m) vs hybrid (configured, fallback to highest)? Open since 2026-08-28.
2. **Selection cost bound**: confirm all (source × method) candidates fit at reference height only during selection; full-height training happens once, for the winner. Any exception (height-dependent methods)?
3. **Height disagreement**: if the winning source/method at reference height plausibly differs at other heights — accept (simplicity) or add per-height selection as an escape hatch?
4. **Cross-mast pre-screening**: Julia's all-ordered-pairs × all-sensors blowup — what pre-filters apply before benchmarking (distance? availability? priority score from ticket 06)?

Context: memory `core://agent/4` records the O(n²) sources (`RecommendTrainMesoCommand` all masts × mesos × 3 methods; redundant full-alignment for one correlation; all ordered mast×mast pairs).

## Answer

Decided 2026-09-01, user-confirmed (grilling round run jointly with ticket 06):

1. **Reference height rule: per (mast × variable).** Two required config fields — `ws_reference_height`, `wd_reference_height` — never optional. Recommend seeds each as the per-mast measured sensor of that type nearest to `reference_height_hint` (recommend-phase parameter, default 160). Rationale: lidar masts measure to 200m, but hub heights rarely exceed 160m — selection anchors near hub height, not mast top. WS and WD sensors on tower masts are typically at different heights (interference avoidance; `CONTEXT.md` Sensor entry), so one height per mast would be wrong. Nearest-sensor always resolves ⇒ exactly one reference height per variable per mast, guaranteed.
2. **Horizontal only.** The reference height binds horizontal scope (cross-mast, meso→mast) exclusively. Vertical selection (tickets 07/08) uses hold-out-layer exams per target height — no reference height exists in vertical scope.
3. **Cost bound.** All (source × method) candidates fit at the reference height only during selection; full-height training happens once, for the winner. No v1 exceptions — v1 methods have no height-dependent structure. With the WS-only pre-rank (ticket 06), selection cost is O(masts + methods × K).
4. **Height disagreement: accepted, no diagnostics.** The heights of interest are typical turbine heights (125/140/160m), strongly correlated with the ~160m reference height — the reference-height winner is almost always the turbine-height winner; quality below 100m is not a concern. No per-height RMSE in the benchmark artifact. A future post-hoc diagnostic command is noted as possible, not committed.
5. **Cross-mast pre-screening.** Feasibility screen pass + WS-only subsampled pre-rank cut at `top_k` (ticket 06). Julia's priority score is dropped; no distance filter (project masts are co-located).

## Acceptance

- [x] Reference-height rule + cost bound recorded under `## Answer`
- [x] Consistent with ticket 06 benchmark protocol
- [x] Map Decisions-so-far updated
- [x] N/A — decision ticket, no code (verify_baseline not applicable)

## Comments

- 2026-09-01 (grilling round, user decisions): **reference height settled.** `reference_height` is a REQUIRED config field per reconstruction set; recommend seeds it as the per-mast measured WS height nearest to `reference_height_hint` (recommend-phase parameter, default 160). Rationale: lidar masts measure to 200m but hub heights rarely exceed 160m — selection must anchor near hub height, not mast top. Nearest-WS always resolves ⇒ exactly one reference height per mast, guaranteed.
- 2026-09-01: **no-optional-fields principle (global).** Recommend materializes every default into explicit config; no optional fields, no runtime fallback defaults. Extends the 2026-08-25 report-heights "recommend proposes, config decides" rule to all reconstruction config.
- 2026-09-01: **scope correction: horizontal only.** Reference height and the reference-height-only benchmark bind horizontal scope (cross-mast, meso→mast) exclusively. Vertical selection (tickets 07/08) uses hold-out-layer exams per target height — no reference height exists in vertical scope.
- 2026-09-01: **cost bound confirmed.** All (source × method) candidates fit at the reference height only during selection; full-height training happens once, for the winner. No v1 exceptions — v1 methods have no height-dependent structure.
- 2026-09-01: **reference height is per (mast × variable), not per mast.** WS and WD sensors on tower masts are typically at different heights (interference avoidance; recorded in repo-root `CONTEXT.md` under Sensor). The horizontal benchmark therefore resolves two reference heights per mast — `ws_reference_height` (nearest WS sensor to the hint) and `wd_reference_height` (nearest WD sensor to the hint) — both required config, both seeded by recommend from the same `reference_height_hint` (default 160). WS method selection benchmarks at the WS reference height; WD selection at the WD reference height. The availability gate (ticket 06 Q5) is likewise per-variable, measured at that variable's reference height.
- 2026-09-01 (Q3, user decision): **height disagreement accepted, no diagnostics in v1.** Rationale: the heights of interest are typical turbine heights (125/140/160m), whose wind is strongly correlated with the ~160m reference height — the reference-height winner is almost always the turbine-height winner; quality below 100m is not a concern. No per-height RMSE in the benchmark artifact. A future post-hoc diagnostic command (compare winner vs runner-up across heights) is noted as possible but not committed work.

- 2026-09-02 (ticket 06 amendment, user): "full-height training happens once, for the winner" now reads **once per winner** — the multi-winner fill-span cover (ticket 06 `## Amendments`, 2026-09-02) can crown several winners per (mast × sensor type) when fillable spans are complementary; each winner trains all target heights.
