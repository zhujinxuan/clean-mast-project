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
