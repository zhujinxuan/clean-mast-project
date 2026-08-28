# 03 — 2.6.1 static IEC table: correct Vref/Ve50 semantics

**What to build:** `IEC_STANDARDS_DATA` (iec_atom.py) currently lists
vref = 10/8.5/7.5 — those are IEC 61400-1 **Va** (annual-average reference,
0.2 × Vref), mislabeled as Vref. The classification logic and the handwritten
report both use the 50-year quantities: sustained reference 50/42.5/37.5 and
50-year extreme gust 70/59.5/52.5.

Rewrite the static reference table to standard semantics (the handwritten
table's values, with IEC-correct names — the handwritten labels Ve50/Vref are
swapped): 风区等级 | Vref 50年一遇持续风速参考值(m/s) | Ve50 50年一遇极大风速
(m/s) → I 50/70, II 42.5/59.5, III 37.5/52.5, S 场址专用/场址专用. Keep the
IEC 61400-1 caption.

**Blocked by:** None — can start immediately

**Status:** done

## Scope

- `extreme_wind/model/iec_atom.py`: IEC_STANDARDS_DATA values + column
  headers; caption stays 'IEC 标准风况等级（IEC 61400-1）'.
- Check for other consumers of IEC_STANDARDS_DATA before changing values.
- Update tests asserting the old 10/8.5/7.5 values.

## Acceptance

- Regenerated reports show the corrected 2.6.1 table; classification
  thresholds and the reference table now tell the same story.
- `uv run python scripts/verify_baseline.py --package cleanmast` is green
