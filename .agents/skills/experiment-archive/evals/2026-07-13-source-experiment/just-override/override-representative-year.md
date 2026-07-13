# Override: Representative Year Time Ranges

## Why Override?

The `recommend representative-year` command picks a single 12-month window
that maximizes the number of masts with data. When masts have different
recording periods, this can leave some masts with **zero real data** in the
chosen window — defeating the purpose of calibration.

## Principles

1. **Coverage first**: Each mast gets a window where it has real measurement
   data. Month-start/month-end alignment preferred. Allow up to 4% coverage
   difference between candidate windows.

2. **Prefer later window**: When two windows have comparable coverage (within
   4%), choose the later one. More recent data is generally more representative
   of current conditions.

3. **Per-mast independence**: Each mast can have a different time range.
   The representative year is calibrated per-mast, not globally.

## This Project's Windows

| Mast | Data Range | Window | Coverage | Rationale |
|------|-----------|--------|----------|-----------|
| M3142 | 2022-06-26 → 2023-08-17 | 2022-08-01 → 2023-07-31 | 100% | Only 14mo of data. 08-01 start beats 07-01 (later, same coverage). |
| M5972 | 2022-06-11 → 2023-08-16 | 2022-08-01 → 2023-07-31 | 100% | Same as M3142. |
| M1664 | 2023-01-12 → 2025-12-14 | 2024-09-01 → 2025-08-31 | 98.9% | Best coverage window. 09-01 start. |
| M5057 | 2022-12-29 → 2025-10-22 | 2024-09-01 → 2025-08-31 | 98.4% | Matches M1664 range. Best coverage. |

## Files

- `override_representative_year.py` — Patches `representative-year.toml` with
  per-mast time ranges defined in `MAST_RANGES`.
- Used by `just override-rep-year` and `just rep-year-override`.
