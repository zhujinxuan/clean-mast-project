# Override: Reconstruct-Meso Time Ranges

## Why Override?

`recommend reconstruct-meso` clusters all 4 masts and assigns a single shared
grid: **2022-09-01 → 2025-08-31** (`calculate_cluster_optimal_period`). But the
representative-year windows for M3142/M5972 are **2022-08-01 → 2023-07-31**
(see `override-representative-year.md`), and the representative-year step reads
`./reconstruct-meso/*.parquet` — not `clean/`. The shared grid starting
2022-09-01 silently clipped August 2022, yielding 11-month "representative
years" (48 096 steps instead of 52 560) and `8月: -` rows in the report.

Evidence: `investigation/ws150m-avg-crosscheck/report.md` §4.

## Why Extending Back to 2022-08-01 Is Safe

- `reconstruct-cross/` (the reconstruct-meso input) spans **2022-06-11 →
  2025-12-14** for every mast, 0 nulls at 150m.
- `clean/` has **real measured data** for August 2022 on both masts
  (M3142 clean starts 2022-06-26, M5972 starts 2022-06-11) — the extension
  restores a measured month, not a meso-fabricated one.
- ERA5 meso data covers the period for gap filling.

## Patched Ranges

| Mast | min | max | Note |
|------|-----|-----|------|
| M3142 | 2022-09-01 → **2022-08-01** | 2025-08-31 (unchanged) | cover rep-year window |
| M5972 | 2022-09-01 → **2022-08-01** | 2025-08-31 (unchanged) | cover rep-year window |
| M1664 | 2022-09-01 (unchanged) | 2025-08-31 (unchanged) | rep-year window already inside grid |
| M5057 | 2022-09-01 (unchanged) | 2025-08-31 (unchanged) | rep-year window already inside grid |

## Files

- `override_reconstruct_meso.py` — patches `reconstruct-meso.toml` per-mast
  `time_range` entries defined in `MAST_RANGE_OVERRIDES`.
- Wired into `just recommend-reconstruct-meso` (runs right after the Julia
  recommend step), mirroring the `recommend-representative-year` pattern.

## Downstream Reminder

After changing `reconstruct-meso.toml`, rerun for full effect:
`process-reconstruct-meso` → `fill-heights-meso` → `process-representative-year`
→ `fill-heights-representative-year` → `process-wt-timeseries` → `report-timeseries`.
The rep-year windows and `rep-ts-report.toml` analysis windows stay at
2022-08-01 → 2023-07-31 for M3142/M5972 — now fully covered.
