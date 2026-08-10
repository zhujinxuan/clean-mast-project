# 04 — Fix ghost names and content errors in leaf specs

**What to build:** Correct per-leaf content defects that survive the boilerplate strip: ghost class names, aspirational claims, self-contradictory rules, and code-WHAT leaked into 业务说明. Files: `extreme_wind`, `weibull`, `turbulence`, `wind_rose`, `representative_year` specs. Details in `.scratch/spec-docs-cleanup/findings.md`.

**Blocked by:** 01-leaf-boilerplate-dedup (same files; boilerplate must leave first)

**Status:** done

extreme_wind/spec.md:

- [x] Qualify the Gumbel coverage claim: fitting currently covers sustained (avg) sensors only; max-sensor fit is tracked in `.scratch/reporting-extreme-wind-gumbel/issues/01-extreme-sensor-gumbel-fit.md`
- [x] Resolve the Path()-sentinel contradiction (rule 11 prescribes it, anti-pattern line 19 bans it) — one positive statement; note the convention now lives in reporting/spec.md
- [x] Replace the "NoMast atom" ghost with the real mechanism: `IECStandardsAtomMeta` with `mast_name: str = "_no_mast"` (`model/report_meta.py`)
- [x] Correct the business text: Gumbel fits 5-day maxima (五日最大法, `extract_five_day_maxima`), not annual maxima

weibull/spec.md:

- [x] Replace the ghost class `WeibullFitter` with the real API: module-level `fit_weibull` in `compute.py`; never introduce a stateful fitter class
- [x] Remove the code-WHAT clause from 业务说明 Key concepts (keep the k-parameter domain semantics)

turbulence/spec.md:

- [x] Collapse the triple statelessness statement into one rule + one anti-pattern
- [x] Add "A+" to the business category list (code returns A+/A/B/C)
- [x] Remove the code-WHAT clause from 业务说明 Key concepts

wind_rose/spec.md:

- [x] Drop the duplicated magic-number anti-pattern (the rule already carries the positive)

representative_year/spec.md:

- [x] Delete the "非政治性" no-op clarification; state the 4×4 grid fact once (Purpose only)
- [x] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- From the 2026-08-10 spec-docs review. Full quotes in `../findings.md`.
- Resolved 2026-08-10. Note: the extreme_wind Gumbel-qualification criterion became moot — the max-sensor Gumbel fit was implemented first (commit 20a1ce80), so the Purpose claim is now accurate as written. Applied: NoMast ghost → `IECStandardsAtomMeta` (`mast_name="_no_mast"`); Path()-sentinel contradiction resolved (altair-types rule for subgrid helpers, sentinel convention owned by reporting/spec.md); business text corrected to 五日最大值序列; weibull rule names real `fit_weibull`; turbulence statelessness collapsed to one rule + one anti-pattern and A+ added; wind_rose duplicated magic-number anti-pattern dropped; representative_year 非政治性 no-op removed and rules slimmed to the calibration-payload fact.
