# 19 — Research: WD ε threshold — direction-sensor accuracy evidence

**Type:** research

**Status:** resolved

**Blocked by:** None

## Question

What ε (degrees) should the ε-group sort use when ranking WD candidates? Ticket 07 set ε = 2° for vertical ("smaller gaps are below direction-sensor accuracy ≈ noise"); ticket 15 was about to copy it horizontally when the user flagged: **2° may be too small — common mast WD sensors carry a documented 误差许可 (permissible error) we can reference.**

The ε semantic: candidates whose primary-metric (wrapped-MAE) gap is < ε are grouped as ties, and the secondary metric (circular-mean bias) breaks the tie. ε too small → noise ranks as signal; ε too large → real skill differences collapse into ties.

Investigate:

1. **Instrument accuracy specs (误差许可)**: documented accuracy of common mast WD sensors — NRG 200P, Thies First Class (4.3351), Vector A100, MetOne 024A, Vaisala WAV — within their operating speed range, and any accuracy degradation at low speed. Include Chinese 规范 instrumentation requirements (GB/T 18710 / NB/T 31147 sensor permissible-error annexes, if they specify direction accuracy).
2. **Total direction uncertainty in practice**: sensor spec + mounting/alignment/boom-orientation error as documented in MEASNET site-assessment guidance, IEC 61400-12-1 direction-measurement uncertainty budgets, and calibration-lab practice. (Field alignment error alone is commonly several degrees — quantify from sources.)
3. **Meaningful-gap evidence**: what wrapped-MAE gap between two reconstruction candidates is statistically meaningful given monthly-fold noise — any published MCP/WD-reconstruction comparisons reporting WD skill differences and their significance?
4. **Cross-scope consequence**: if the evidence supports ε > 2°, does the argument apply to vertical too (ticket 07's ε would be amended) — i.e., is there any reason horizontal and vertical WD ε should differ?

Feeds ticket 15 Q3 (horizontal ε) and possibly amends ticket 07 (vertical ε).

## Acceptance

- [ ] Findings at `research/wd-epsilon.md`, every claim cited to a primary source
- [ ] Verdict section: (a) documented sensor 误差许可 values, (b) total field direction-uncertainty budget, (c) recommended ε with justification, (d) whether vertical ε (ticket 07) should be amended
- [ ] Answer recorded under `## Answer`; map Decisions-so-far updated
- [ ] N/A — research ticket, no code (verify_baseline not applicable)

## Comments

- 2026-09-02: created mid-grilling on ticket 15 (user request). Ticket 15's Q1/Q2/Q4 are decided; Q3 (ε value) parks on this research. User intuition: 2° too small.

## Answer

Resolved 2026-09-02 (research subagent; findings with full citations: `research/wd-epsilon.md`):

1. **误差许可 (documented)**: GB/T 18709-2002 §5.1.2.2 vane ±2.5° (plus §6.2.2.3 true-north installation requirement); NB/T 31147-2018 ≤±1° accuracy, ≤0.5° resolution; NREL/AWS handbook ≤5° system error. Datasheets: NRG 200P ±4.3° (k=2, +4–8° dead band), Vector W200P ±3° (±2° calibrated), Thies First Class 4.3151 ±1°, Met One 024A ±5°, Vaisala WAV151 <±3° with 5.6° quantization. GB/T 18710 has no accuracy clause.
2. **Field budget**: alignment dominates — lab vane calibration ≈0.8° (k=2), but field north/boom alignment is the big term (MEASNET V3 mandates but doesn't quantify it; a documented well-built 46 m mast measured 16.14° ± 2.13° misalignment; Geovane-class referencing gets <1°). Legacy fleet total ≈ ±3–5° (fixed per-sensor bias); ≈ ±2° only with a First-Class sensor + Geovane-class north reference.
3. **Recommended ε = 5° (both scopes)**: matches the loosest legacy fleet specs, envelopes sensor⊕alignment RSS, sits above monthly-fold gap noise (~0.5–3°) yet far below the 22.5–30° sector granularity at which direction is consumed. A 2° floor is honest only on masts documented with ±1°-class sensor AND <1° north referencing.
4. **Ticket 07 amendment recommended**: vertical ε = 2° → 5° — both exams score against a target-mast vane with identical truth uncertainty; horizontal's larger source errors inflate the MAE level, not the tie floor; one uniform ε keeps both benchmark commands' semantics comparable. (User confirmation pending on ticket 15.)
