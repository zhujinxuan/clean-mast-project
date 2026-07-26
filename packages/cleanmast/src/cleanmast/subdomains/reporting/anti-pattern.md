# Anti-Patterns — Reporting Subdomain

Audit date: 2026-06-26. Updated: 2026-07-26. Checked against `reporting/spec.md` and `subdomains/spec.md`.

> Resolved entries (V1–V6, S2, S11, D1) removed 2026-07-21. Waves 1–4
> (V7, V8, S13, S6-F821; S8, S9, S12, S7; S10; S4, S6-E402) and S14 resolved
> 2026-07-26 — baseline gate green after each wave.
> S7 fully resolved: heights-of-interest are now config-driven. `recommend`
> discovers `analysis_heights` (WS-avg in 120–160m) and `temporal_heights`
> (all WS-avg heights) onto MastRef; wind_frequency / weibull /
> representative_year consume `analysis_heights`, temporal consumes
> `temporal_heights`, and every height-driven subsection (incl. turbulence and
> extreme_wind) now raises if its heights field is empty at generation time.
> Intended report deltas: temporal shows all WS-avg heights (was a >=100
> chart filter); wind_frequency/weibull use inclusive 120–160 (was >120).
> Only S3 remains open.

---

## VIOLATIONS

None open.

---

## SMELLS

### S3. `Any` type usage / bare container types

**Files**:
- `subdomains/extreme_wind/section.py` — 5× `list[dict[str, Any]]` (lines 299, 346, 347, 447, 448)
- `subdomains/extreme_wind/compute/__init__.py` — `dict[str, Any]` return types + `list[dict[str, Any]]` accumulators (lines 110, 152, 184, 218, 319)
- `subdomains/extreme_wind/model/gumbel_qq.py:203` — bare `list[dict]`
- `subdomains/wind_temporal/compute.py` — 3× bare `list[dict]` (lines 97, 147, 200)
- `subdomains/turbulence/compute.py:197` — bare `list[dict]`
- `subdomains/representative_year/assemble.py` — 2× bare `list[dict]` (lines 38, 98)
- `subdomains/representative_year/compute.py` — unannotated `item` params (lines 140, 340) + bare `inputs: list` (line 397)

**Issue**: `Any` erases type safety. Bare `list[dict]` without value types makes static analysis and refactoring unreliable. These should be replaced with typed `TypedDict`, `NamedTuple`, or Pydantic models.
