# 18 — Research: benchmarking rep-year calibration methods; short-observation case

**Type:** research

**Status:** resolved

**Blocked by:** None

## Question

Two linked questions:

1. **Can/should representative-year calibration methods be benchmarked, and how?** Candidate exam design: on a long reference (meso) record, simulate a short measurement campaign — hold out years, calibrate the pseudo-campaign against a pseudo-climatology, score the calibrated series against the actual long-term statistics. Is this or another validation design documented in practice or literature?
2. **When the mast observation is one year or less, what does practice do?** Minimum-duration guidance, seasonal-coverage requirements, uncertainty inflation, or refusal to correct?

Investigate:

1. **Measurement-duration standards**: MEASNET guidance on campaign length (is a full year required for seasonal coverage?), IEC 61400-12-1 / 61400-15 (long-term correction uncertainty as a function of on-site record length), FGW TR6, Chinese 规范 requirements (GB/T 18710 / NB/T — minimum measurement duration, typically ≥1 full year? consequences if shorter?).
2. **MCP skill vs overlap length**: literature on how long-term correction error grows as the concurrent period shrinks below one year; any minimum-overlap rules of thumb with evidence behind them.
3. **Validation designs for long-term correction**: hindcast / hold-out-years exams on long reference records; synthetic benchmarks; published comparisons of correction methods scored against known long-term truth.
4. **Industry tool behavior**: what Windographer/WindPRO/OpenOA do or warn when the on-site record is < 1 year (seasonal completeness checks, uncertainty multipliers, hard limits?).

Context: ticket 09 set `min_overlap_months` default 0 — sub-year masts stay pairable for horizontal reconstruction; the open question is what the rep-year phase should do with them. Our benchmark machinery (monthly blocked bootstrap, ε-group sort) has no calibration-exam analogue — this research decides whether one is worth designing.

Feeds ticket 12 Q4 (whether calibration methods benchmark, and how) and the short-mast policy for the rep-year phase.

## Acceptance

- [ ] Findings at `research/rep-year-benchmarking.md`, every claim cited to a primary source
- [ ] Verdict section: (a) documented minimum-duration/seasonal-coverage rules, (b) whether calibration-method benchmarking is done in practice and which exam design, (c) evidence on MCP skill vs overlap length, (d) concrete v1 recommendation: benchmark or not, and short-mast policy (correct-with-uncertainty / refuse / flag)
- [ ] Answer recorded under `## Answer`; map Decisions-so-far updated
- [ ] N/A — research ticket, no code (verify_baseline not applicable)

## Comments

- 2026-09-02: created mid-grilling on ticket 12 (user request). Ticket 12's Q4 (do calibration methods benchmark) parks on this research — my flat "no benchmark" recommendation was made without the short-record evidence this ticket gathers.

## Answer

Resolved 2026-09-02 (research subagent; findings with full citations: `research/rep-year-benchmarking.md`):

1. **Minimum duration**: 12 complete consecutive months is the normative minimum everywhere (MEASNET v3 §7.2 shall-level; FGW TR6; GB/T 18709/18710 + NB/T 31147 ≥1 year, ≥90% effective completeness; IEC 61400-15-1 seasonal representativeness + shall-level duty to long-term-adjust). No standard forbids sub-year data — the documented route is a declared deviation with significantly increased uncertainty.
2. **Calibration benchmarking IS documented practice**: contiguous pseudo-campaign windows held out of long records, corrected, scored against known long-term statistics (Basse 2021, Sheridan 2025, Weekes & Tomlin 2014, Miguel 2019, RECAST 2021); within-record slicing ships in Windographer (bootstrap Test MCP Uncertainty) and windPRO (slicing tests, summer/winter-leakage warnings); MEASNET mandates a self-consistency test.
3. **Skill vs overlap**: error falls monotonically with overlap, cliff below ~3 months; ~4–4.8% mean-WS error at 3 months; 1–2-month weakly-correlated windows can be WORSE than no correction (Sheridan: worst-case CF errors 47/26/16% at 1/3/6 months); even perfect seasonal-bias knowledge leaves ~3× uncertainty at 1–2 months (RECAST); season matters (avoid Jul–Aug); record length dominates method choice.
4. **v1 recommendation**: (d-1) do NOT build a calibration benchmark in v1 — one method, nothing to select; overlap length and seasonal coverage dominate error. Benchmark when the 行标 two-stage (registry's second `repyear.*` method) lands, reusing the documented hold-out-window exam on the meso record; meanwhile log MEASNET §8.3.2 MBE/MAE/RMSE in-sample diagnostics, no gate. (d-2) Short-mast policy: tiered correct-with-uncertainty — ≥12 months calibrate normally; 6–11 months correct+flag; 3–5 months correct only if r ≥ 0.7 correlation gate passes (always flagged, prefer non-summer overlap); <3 months REFUSE with skip flag; every tier requires unbiased monthly coverage in the used overlap.

- 2026-09-02 (user question during ticket 12 grilling): **exam design sketch for when a second `repyear.*` method registers** (not v1 scope; recorded for the future benchmark command): pseudo-campaigns on long records (multi-year masts, else a second meso dataset as pseudo-mast) — keep only a contiguous window W ∈ {12, 6, 3} months as "measured"; each candidate method trains slopes on W's overlap with the reference and calibrates; score corrected long-term mean against the target's known full-record climatology (mean-WS error primary, bias secondary, mean-ws³ energy proxy diagnostic); repeat W at every start month (≥12 windows per length) across sites/references — paired comparison, same ε-group sort machinery as ticket 06; contiguous blocks only, never row-level resampling.
