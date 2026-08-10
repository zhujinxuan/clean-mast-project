# 04 — Fix ghost names and content errors in leaf specs

**What to build:** Correct per-leaf content defects that survive the boilerplate strip: ghost class names, aspirational claims, self-contradictory rules, and code-WHAT leaked into 业务说明. Files: `extreme_wind`, `weibull`, `turbulence`, `wind_rose`, `representative_year` specs. Details in `.scratch/spec-docs-cleanup/findings.md`.

**Blocked by:** 01-leaf-boilerplate-dedup (same files; boilerplate must leave first)

**Status:** ready-for-agent

extreme_wind/spec.md:

- [ ] Qualify the Gumbel coverage claim: fitting currently covers sustained (avg) sensors only; max-sensor fit is tracked in `.scratch/reporting-extreme-wind-gumbel/issues/01-extreme-sensor-gumbel-fit.md`
- [ ] Resolve the Path()-sentinel contradiction (rule 11 prescribes it, anti-pattern line 19 bans it) — one positive statement; note the convention now lives in reporting/spec.md
- [ ] Replace the "NoMast atom" ghost with the real mechanism: `IECStandardsAtomMeta` with `mast_name: str = "_no_mast"` (`model/report_meta.py`)
- [ ] Correct the business text: Gumbel fits 5-day maxima (五日最大法, `extract_five_day_maxima`), not annual maxima

weibull/spec.md:

- [ ] Replace the ghost class `WeibullFitter` with the real API: module-level `fit_weibull` in `compute.py`; never introduce a stateful fitter class
- [ ] Remove the code-WHAT clause from 业务说明 Key concepts (keep the k-parameter domain semantics)

turbulence/spec.md:

- [ ] Collapse the triple statelessness statement into one rule + one anti-pattern
- [ ] Add "A+" to the business category list (code returns A+/A/B/C)
- [ ] Remove the code-WHAT clause from 业务说明 Key concepts

wind_rose/spec.md:

- [ ] Drop the duplicated magic-number anti-pattern (the rule already carries the positive)

representative_year/spec.md:

- [ ] Delete the "非政治性" no-op clarification; state the 4×4 grid fact once (Purpose only)
- [ ] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- From the 2026-08-10 spec-docs review. Full quotes in `../findings.md`.
