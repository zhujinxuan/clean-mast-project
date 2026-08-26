# Turbulence IEC band fix — feature spec

## Problem

The turbulence section (2.4.7) disagrees with itself. Per-bin tables and the
multi-height IEC band chart use band-membership classification (representative
TI above the C reference curve ⇒ IEC B), but the summary sentence
("暂定为 IEC X 类") inlines a second, stricter threshold chain (B only when
above the B curve) — one band lower. On kp-202603 test data:

- Per-bin rows: bins 14–15 / 15–16 both classify **B** (rep TI 0.147 / 0.146).
- Summary sentence: **"暂定为 IEC C 类"** (mean rep TI 0.1447 < B curve 0.1573
  at 15 m/s).

Root cause: duplicated classification logic. `compute.py` has
`classify_iec_category` (band membership); `turbulence_summary_atom.py`
re-implements thresholds inline (exceed-the-curve). The summary atom also
averages representative TI across bins 14–16 and heights before classifying
once, diluting high bins.

## Decisions (user-approved 2026-08-26)

- **Classification convention**: band membership, single implementation in
  `model/iec.py` (model layer; compute builds on model, never reverse).
- **Summary table (湍流强度统计表)**: only the 14.5–15.5 m/s band per
  interested height; drop ">3 m/s" and "9.5–10.5 m/s" rows; add 数据点数
  column (sum of bin counts).
- **Band convention**: bin-center membership. 14.5–15.5 m/s = bins 14 and 15
  (centers 14.5 / 15.5). This matches existing labels (9.5–10.5 = bins 9,10).
- **Summary sentence**: values from the same 14.5–15.5 band so sentence
  numbers equal table row numbers; classification via the shared classifier
  at 15 m/s on the mean across heights (existing aggregation shape kept).

## Expected output delta (kp-202603-report)

- Sentence: IEC C → **B** for both L32261 and M245228; per-height values
  recomputed over bins 14,15 only.
- Table 24 (and M245228 twin): 3 rows (120/140/160m) × 14.5–15.5 m/s with
  数据点数; >3 and 9.5–10.5 rows gone.
- Per-height bin tables and multi-height chart: unchanged.

## Tickets

- `issues/01-unify-iec-classification.md` — one classifier, correct semantics
- `issues/02-summary-table-band-count.md` — 14.5–15.5 band + 数据点数 column
- `issues/03-spec-updates-regression-tests.md` — spec.md + tests lock it in
