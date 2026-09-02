# 08 — Vertical interpolation methods

**Type:** grilling

**Status:** resolved

**Blocked by:** None

## Question

Fix the interpolation method set for WS-interpolate and WD-interpolate. User steer: interpolation is normally not complex — keep the candidate set small.

Decide:

1. **WS interpolation**: log-linear in ln(z) between bracketing heights, per timestamp — is any competitor worth benchmarking (power-law two-point, plain linear)? Or is log-linear accepted without benchmark?
2. **WD interpolation**: circular linear interpolation between bracketing heights, weighted by ln(z)? Wraparound handling (0/360) must be specified.
3. **Per-height-interval parameters**: user noted interpolation shear can differ per height interval — does the fit artifact carry per-interval parameters (one fit covering all intervals vs one fit per interval)?
4. **Exam design**: hold out a middle layer, same blocked bootstrap? Or is interpolation accepted on principle with spot-checks?
5. **Coexistence with extrapolation**: one mast's vertical strategy = interpolation fits for gaps between measured layers + extrapolation fit above top layer; how the unified fill picks per target height.

## Answer

Decided 2026-09-01, user-confirmed (grilling, several rounds incl. an evidence check on veer physics):

1. **WS interpolation = one power-law blend family**: `vertical.ws.interpolate.powerlaw.<layer-scheme>.<scale>`, v1 layer scheme `brackets`, scales `{10min, 1h, month, series}`. Predict at timestamp $t$ for target $z$ between bracketing observed layers $(z_{lo}, z_{hi})$: two one-sided power-law estimates $\hat u_{lo} = u_{lo}(t)\cdot(z/z_{lo})^{\bar\alpha}$, $\hat u_{hi} = u_{hi}(t)\cdot(z/z_{hi})^{\bar\alpha}$, blended $\hat u = (1-w)\hat u_{lo} + w\hat u_{hi}$ with ln-$z$ distance weight $w = \ln(z/z_{lo})/\ln(z_{hi}/z_{lo})$ (log-law grounded for speed). At `10min`, $\bar\alpha = \alpha_t$ from the bracket pair at $t$; the two estimates coincide and the method degenerates to the exact per-timestamp two-point power law. **Log-linear dropped from v1** (规范-consistency, the same rule as ticket 05's log-law exclusion) — amends 05/07, where loglinear was a registered benchmarked candidate.

2. **WD interpolation mirrors the family**: `vertical.wd.interpolate.linear.brackets.<10min|1h|month|series>` (user naming call: `linear`, not `circular`). The method definition must state that `linear` means **linear-in-$z$ on the circle** — offset-based wrapped arithmetic, wrap to $(-180°, 180°]$, an exactly-180° difference resolving to $+180°$ (deterministic, no degenerate case — vector interpolation rejected); never naive degree arithmetic, which breaks across 0/360. Same blend structure as WS: per-interval veer offsets applied linear in $z$, $w_z = (z - z_{lo})/(z_{hi} - z_{lo})$. **Linear-$z$, not ln-$z$** (user ruling after evidence check): no source supports ln $z$ for veer — Ekman turning is ≈ linear in $z$ over mast spans ($h_{Ek} \sim 300$–$1000$ m), Kelly & van der Laan 2023's practical form is steeper than ln $z$, and surface-layer MOST predicts zero veer. The WD exam upgrades from diagnostic-only to a real selection (4 candidates).

3. **Fit-free vs training scales**: `10min` variants are **fit-free** — predict re-derives everything from the observed brackets at predict time; no artifact is trained, persisted, or cached. `1h`/`month`/`series` variants **train**: per adjacent layer pair, per-timestamp $\alpha_t$ (WS) / $\text{veer}_t = \text{wrap}(\theta_{hi}-\theta_{lo})$ (WD) over the pair's training overlap, aggregated to bucket means (24 hour-of-day / 12 calendar-month / 1 whole-series; arithmetic mean for $\alpha$, circular mean for veer); an under-populated bucket (count < `min_points` param) falls back to the next coarser scale's value for that interval. **Fit granularity: one fit per (mast × sensor type × method)** — a table of adjacent intervals, each row carrying its own bucket map (per-interval shear/veer, MEASNET §9.4's per-interval exponents; dissolves the "one fit per interval?" question). Principle recorded: **a method is fit-free iff predict re-derives everything from observed data at predict time.**

4. **Layer scheme is an explicit id segment** (user ruling — no silent defaults), mirroring extrapolate id structure. v1 scheme name: **`brackets`** — the nearest observed layer below and above the target at $t$; truthful under availability routing (a missing middle layer widens the brackets to a non-adjacent observed pair — still the brackets). A future distance-weighted scheme enters additively as `…powerlaw.dist-weighted.<scale>`. Edge case: non-adjacent brackets at $t$ have no trained $\bar\alpha$ → that timestamp degrades to per-timestamp two-point (`10min` behavior, always available since both brackets are observed); no combinatorial pair fitting.

5. **Exam** (per ticket 07): middle-layer hold-out spot-check; qualifying middle layers inside `interpolation_exam_range` (seeded `[125.0, 160.0]`), metrics pooled across (fold × exam layer) before ranking; **one winner per (mast × sensor type × mode = interpolate)**. WS sort: RMSE ascending, ε-group ε=0.05 m/s, bias secondary. WD: wrapped-MAE ε=2° on ws ≥ 3 m/s timestamps, circular-mean bias secondary (per ticket 07). Per-interval mean-$\alpha$/veer diagnostics are recorded in the `benchmark-vertical` artifact — they are exam evidence, not a pseudo-fit.

6. **Default seeds when no exam crowns a winner** (unbenchmarkable / no qualifying middle layer): WS `vertical.ws.interpolate.powerlaw.brackets.10min`, WD `vertical.wd.interpolate.linear.brackets.10min` — fit-free, always available. Replaces ticket 07's `ws.interpolate.powerlaw` / `wd.interpolate.circular` seeds.

7. **Downstream inheritance**: ticket 10 — the cache only handles training methods; `10min` interpolation has no cache key; the provenance manifest's fit-key applies only where a fit exists; strategy config carries the method id alone for fit-free methods. Candidate lists `ws_interpolate_candidates` / `wd_interpolate_candidates` (ticket 07) reseed to the 4-scale families.

## Acceptance

- [x] Interpolation method set + fit granularity recorded under `## Answer`
- [x] Map Decisions-so-far updated
- [x] N/A — decision ticket, no code (verify_baseline not applicable)

## Comments

- 2026-08-31 research (ticket 03, `research/shear-validation.md`) answers most of this ticket: log-linear as default + two-point power-law as the one competitor; per-interval parameters confirmed; exam = middle-layer spot-check only, not full bootstrap. Remaining to decide: wraparound spec for WD circular interpolation, and coexistence with extrapolation at the boundary layer.
- 2026-09-01 (ticket 07, resolved): interpolation exam = middle-layer hold-out spot-check restricted to middle layers inside `interpolation_exam_range` (required benchmark-config field, seeded [125.0, 160.0]); no qualifying middle layer → no exam → default seed `vertical.ws.interpolate.powerlaw` (规范-consistency overruled the research's log-linear default — log-linear stays a benchmarked candidate where an exam runs). Boundary coexistence settled in 07: per-timestamp routing by availability (observed layer above target → interpolate; else extrapolate anchored at the highest observed layer below; filled values never anchor; no blend). Still owned here: WD circular wraparound spec, per-interval fit-artifact shape.
