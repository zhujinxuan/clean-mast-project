# Fix: wind rose frequency inflated by missing month×sector rows (no zero-fill)

Status: ready-for-agent
Type: task
Blocked by: none

## Summary

Wind rose 风向频率 and 风能频率 (monthly-mean口径) are systematically
overestimated for seasonally-absent sectors: 16-sector frequencies sum to
>100%. Example (2096 @150m representative year): WSW reported 21.1% vs true
17.6% (+3.5pp).

## Root cause

`wind_rose/compute.py::_process_sensor_data` groups by `(month, sector)`;
`group_by` emits no row for a zero-count combination. Downstream atoms
(`wind_rose_atom.py` lines 60, 145, 175, 228, 315, 345 — table, chart,
summary, both frequency and energy variants) average `frequency` /
`energy_frequency` with `pl.col(...).mean()`, whose denominator becomes
"months the sector appeared" instead of "months with data".

## Fix (decided)

In `compute.py::_process_sensor_data`, after computing `month_sector_stats`,
zero-fill the full grid before returning:

- Grid = (months present in this sensor's data) × (sectors 0..15),
  cross-joined, left-joined to `month_sector_stats`.
- Do **not** hardcode months 1..12: a month with no data at all is missing
  data, not zero frequency. Only month×sector gaps within observed months
  are true zeros.
- Fill: `count = 0`, `frequency = 0.0`, `total_power = 0`,
  `wind_power_density` → null or 0 (never sampled; 0.0 is fine, the
  per-sector mean wind speed is not consumed by any atom), `month_name`
  derived from month, `sector_name` from `SECTOR_LABELS`.
- `_compute_energy_frequency` then yields 0 for filled rows naturally.

One fix site covers all 7 aggregation sites in both atoms; Grid variants
share the same frame and need no change.

## Acceptance criteria

- [ ] Regression test (pseudo data: 11 months all-N, 1 month all-S, one
      sample/day) asserts N = 11/12 ≈ 91.7%, S = 1/12 ≈ 8.3%, all-sector
      frequency sum = 1.0 per height — fails on current code, passes after
      fix.
- [ ] Same-style test for `energy_frequency` zero-fill (or covered by the
      same test asserting sum = 1.0).
- [ ] No other behavior change: sectors present every month keep identical
      values.
- [ ] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Primary sources

- Bug report: `C:\Users\zhu_j\Downloads\wind-rose-frequency-bug.md`
  (phenomenon, root cause, repro script, verification values)
- Fix locus: `packages/cleanmast/src/cleanmast/subdomains/reporting/subdomains/wind_rose/compute.py`

## Comments

- 2026-09-09: Filed from user-supplied bug document. Grilling skipped —
  document fully specifies root cause, fix locus, and verification values;
  the only open micro-decision (fill grid = observed months, not hardcoded
  1..12) resolved above.
