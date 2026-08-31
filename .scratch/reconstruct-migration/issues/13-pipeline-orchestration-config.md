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

## Acceptance

- [ ] Config schema + orchestration design recorded under `## Answer`
- [ ] Map Decisions-so-far updated
- [ ] N/A — decision ticket, no code (verify_baseline not applicable)
