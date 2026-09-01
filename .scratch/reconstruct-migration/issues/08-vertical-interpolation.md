# 08 — Vertical interpolation methods

**Type:** grilling

**Status:** ready-for-human

**Blocked by:** None

## Question

Fix the interpolation method set for WS-interpolate and WD-interpolate. User steer: interpolation is normally not complex — keep the candidate set small.

Decide:

1. **WS interpolation**: log-linear in ln(z) between bracketing heights, per timestamp — is any competitor worth benchmarking (power-law two-point, plain linear)? Or is log-linear accepted without benchmark?
2. **WD interpolation**: circular linear interpolation between bracketing heights, weighted by ln(z)? Wraparound handling (0/360) must be specified.
3. **Per-height-interval parameters**: user noted interpolation shear can differ per height interval — does the fit artifact carry per-interval parameters (one fit covering all intervals vs one fit per interval)?
4. **Exam design**: hold out a middle layer, same blocked bootstrap? Or is interpolation accepted on principle with spot-checks?
5. **Coexistence with extrapolation**: one mast's vertical strategy = interpolation fits for gaps between measured layers + extrapolation fit above top layer; how the unified fill picks per target height.

## Acceptance

- [ ] Interpolation method set + fit granularity recorded under `## Answer`
- [ ] Map Decisions-so-far updated
- [ ] N/A — decision ticket, no code (verify_baseline not applicable)

## Comments

- 2026-08-31 research (ticket 03, `research/shear-validation.md`) answers most of this ticket: log-linear as default + two-point power-law as the one competitor; per-interval parameters confirmed; exam = middle-layer spot-check only, not full bootstrap. Remaining to decide: wraparound spec for WD circular interpolation, and coexistence with extrapolation at the boundary layer.
- 2026-09-01 (ticket 07, resolved): interpolation exam = middle-layer hold-out spot-check restricted to middle layers inside `interpolation_exam_range` (required benchmark-config field, seeded [125.0, 160.0]); no qualifying middle layer → no exam → default seed `vertical.ws.interpolate.powerlaw` (规范-consistency overruled the research's log-linear default — log-linear stays a benchmarked candidate where an exam runs). Boundary coexistence settled in 07: per-timestamp routing by availability (observed layer above target → interpolate; else extrapolate anchored at the highest observed layer below; filled values never anchor; no blend). Still owned here: WD circular wraparound spec, per-interval fit-artifact shape.
