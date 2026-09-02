# 13 — Pipeline orchestration and run-phase config

**Type:** grilling

**Status:** ready-for-human

**Blocked by:** 04-operator-contract-timerange, 09-feasibility-screen, 10-fit-artifact-cache

## Question

Design the run-phase configuration and CLI orchestration (charted in ticket 01, decision 9: config carries an explicit strategy per reconstruction set; benchmark winner is the seeded default, user-overridable).

Decide:

1. **Reconstruction set config block**: exact fields — source, target, method id, timerange, heights, fallback chain ref; Pydantic IR placement (existing config IR for reconstruct-meso / representative-year is Julia-matched — extend or replace?).
2. **Pipeline order enforcement**: data clean → reconstruct-single → reconstruct-cross → reconstruct-meso → representative-year; fill-heights after meso and after rep-year. Enforced how — one orchestrating command, stage commands with ordering checks, or documented convention?
3. **Recommend → run UX**: recommend runs screen + benchmark, writes recommendation artifact + seeded config; run consumes config as-is. Diff/review surface for user overrides?
4. **Fill-heights at two points**: same selected vertical fit reused after meso and after rep-year (missing-only) — how config expresses the two invocation points.
5. **train-meso config model**: the one missing config IR piece (memory `core://agent/4`) — is it subsumed by reconstruction-set config + fit cache, or still needed?

- 2026-09-02 (ticket 10, resolved): **Q5 is pre-answered — the train-meso config IR is subsumed.** The fit cache is keyed by (method, refs, training overlap, params-only hash) computed from the run-phase strategy config, whose params block is materialized by recommend as required fields. There is no separate train phase, no train command, and nothing left for a standalone train-meso config model to carry: strategy config (method id + params + refs) + cache cover training entirely.

## Acceptance

- [ ] Config schema + orchestration design recorded under `## Answer`
- [ ] Map Decisions-so-far updated
- [ ] N/A — decision ticket, no code (verify_baseline not applicable)

## Comments

- 2026-09-01 (user decision, pre-answers Q3): the recommend → run UX is three-phase. Recommend seeds `benchmark-horizontal.toml` + `benchmark-vertical.toml`; the two benchmark commands write their artifacts and seed the run-phase strategy config; run consumes config as-is. Two benchmark commands, not one (rationale in ticket 06 comments, 2026-09-01).

- 2026-08-31 (ticket 04): config schema consequences — per-mast working window per phase (not per-pair); reconstruct-meso window is explicit and independent of report/wt-timeseries windows; `recommend` proposes the meso window length (default policy to decide here: latest N years? anchored on observation?), user overrides via just-override. Config carries strategy identity, with the two reference modes (identity / explicit-artifact + column mapping).

- 2026-09-02 (surfaced during ticket 12 grilling, user scenario): **temporal source composition for cross-mast.** Scenario: masts a (2022-01..2022-12), b (2022-07..2023-06), c (2023-01..2023-12). a→b and c→b are both benchmarkable pairs with *disjoint* fillable spans (a fills b's 2022 era incl. the never-observed 2022-01..2022-06; c fills b's 2023 era). Settled layers: (1) the fit store naturally holds both — cache key carries the source ref, one artifact per (method × source × target sensor) (ticket 10); (2) recommend seeds ONE cross winner per (mast × sensor type) (ticket 06) — the loser's disjoint fillable era falls through to the meso phase; (3) the user can override with two reconstruction sets (a→b, c→b) — both pairs carry benchmark evidence from the same run (all pre-rank survivors get fold metrics), fills stay gated by each pair's persisted fillable spans (disjoint here ⇒ no conflict), and the provenance manifest already records spans → source. **Open for this ticket**: (i) should recommend seed complementary cross sets when candidate pairs' fillable spans are disjoint (multi-winner cross strategy), or stay single-winner + user override? (ii) when two configured sets' fillable spans overlap, what is the fill precedence — config set order? Unspecified today.

- 2026-09-02 (user decision, ticket 06 amendment): sub-question (i) from the a/b/c comment above is **resolved** — recommend seeds complementary cross sets: winner selection is a rank-ordered fill-span cover (multi-winner when fillable spans are complementary), see ticket 06 `## Amendments`. Sub-question (ii) is resolved with it: fill precedence on overlapping spans = winner rank order. Remaining for this ticket: how the seeded strategy config expresses a multi-winner set (one reconstruction set per winner, per sensor type).
