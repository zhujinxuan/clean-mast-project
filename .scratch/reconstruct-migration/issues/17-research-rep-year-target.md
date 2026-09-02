# 17 — Research: representative-year target — actual year vs climatology mean

**Type:** research

**Status:** resolved

**Blocked by:** None

## Question

In wind-resource MCP / long-term (representative-year) correction, should the calibration target be an **actual year** selected from the reference record (a real year whose mean is within a threshold of the long-term mean) or the **climatology mean** itself?

The two semantics under comparison:

- **Actual-year targeting (Julia CleanMast, status quo)**: climatology mean = complete-years mean of the meso record; need-check `|climatology − training-overlap mean| / climatology > 2%`; representative year = the LATEST complete year whose mean is within 2% of the climatology mean; per-sector delta = rep-year meso mean − training-overlap meso mean; apply `mast(t) + delta[sector] × slope[sector]`, sector from meso direction, slopes from the 16-sector OLS fit. Hard error when no year passes the 2% test. (Verified ground truth: `CleanMastProject/src/RepresentativeYear/Analysis.jl`, `Utils.jl`.)
- **Climatology-mean targeting (Chinese 行标 procedure, per ticket 12 comments)**: global correction first — (meso observed-period mean − climatology mean) applied globally — then a linear fit per 16 sectors binned by the MAST direction, then reduce. No representative-year selection step; the target is the climatology mean itself.

Investigate:

1. **Standards & industry guidance**: MEASNET MCP guidance, IEC 61400-12-1 / 61400-15, DNV (legacy Risø), FGW TR6, Chinese standards (GB/T 18710, NB/T wind-resource standards — is the 行标 two-stage procedure as described?), IEA Wind Task guidance. What target does each prescribe or imply?
2. **Industry tools**: Windographer MCP, WindPRO long-term correction, WAsP, open-source (OpenOA, brightwind) — actual representative year vs scale/regress toward the long-term mean?
3. **Published evidence on consequences**: does the choice measurably affect AEP, distribution shape, or uncertainty? Arguments to test: a real year preserves physically coherent temporal/sectoral structure (seasonality, autocorrelation, sector distribution) vs the climatology mean being a synthetic construct; conversely mean-targeting avoids single-year selection noise.
4. **Threshold practice**: is a ~2% representativeness threshold + latest-qualifying-year rule documented anywhere, or CleanMast-local? Documented fallbacks when no year qualifies?

Feeds ticket 12 Q3 (semantics fidelity): whether v1 keeps Julia actual-year targeting, and what the no-qualifying-year failure mode should be.

## Acceptance

- [ ] Findings at `research/rep-year-target.md`, every claim cited to a primary source
- [ ] Verdict section: (a) standard practice where documented, (b) evidence weight actual-year vs climatology-mean, (c) v1 design implications, (d) no-qualifying-year failure mode (hard error vs nearest-year fallback)
- [ ] Answer recorded under `## Answer`; map Decisions-so-far updated
- [ ] N/A — research ticket, no code (verify_baseline not applicable)

## Comments

- 2026-09-02: created mid-grilling on ticket 12 (user request) — the actual-year-vs-climatology-mean question graduated into its own research ticket. Ticket 12's Q3 sub-point (hard error vs fallback) parks on this research.

## Answer

Resolved 2026-09-02 (research subagent; findings with full citations: `research/rep-year-target.md`):

1. **No standard or tool selects an actual representative year.** IEC 61400-15-1 §5.2.1, MEASNET V3 §8.3, FGW TR6 Rev.12, DNV WindFarmer, Windographer, WindPRO, WAsP/windkit, OpenOA, brightwind — all target the long-term climatology over a ≥10-yr reference via regression/scaling. GB/T 18710-2002 is the closest to CleanMast's algebra (16-sector additive delta on the mast series, Appendix A verbatim) but anchors the delta at the **multi-year mean**; its 代表年 means a representative hourly dataset, not a chosen calendar year.
2. **2% gate**: one documented analog — NB/T 31147-2018 §5.2 triggers representative-year correction when annual-mean deviation exceeds 2%. The latest-qualifying-year tiebreak is CleanMast-local (documented nowhere; TMY/WRY select by statistics, not recency).
3. **Evidence**: no study benchmarks actual-year vs climatology anchoring directly; both semantics keep the mast year as the time-series substrate, so the actual-year pick only perturbs the target mean by a bounded (≤2%) year effect — while accepting that year's direction/Weibull-shape atypicality (MEASNET's documented single-year caveat). Inter-annual noise is 4–10% in speed, 6–30% in energy (Bodini 2016).
4. **v1 recommendation**: keep the additive per-sector delta × slope correction; **switch the anchor from the selected rep-year meso mean to the complete-years climatology mean** (GB/T 18710/NB/T fidelity + MEASNET/IEC/tool alignment); keep the 2% check as a reporting/uncertainty flag rather than a hard gate; actual-year mode as an optional additive variant. Under climatology anchoring the no-qualifying-year failure mode disappears by construction; if actual-year mode is kept, hard error is the defensible default — no surveyed standard silently substitutes (MEASNET substitute-uncertainty, FGW SOLL justify+uncertainty).
