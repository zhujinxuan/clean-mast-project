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
