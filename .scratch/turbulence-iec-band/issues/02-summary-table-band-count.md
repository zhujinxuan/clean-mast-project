# 02 — Summary table: 14.5–15.5 m/s band only, add 数据点数

**What to build:** `SingleMastTurbulenceSummaryAtom.renderTable` drops the
">3 m/s" and "9.5–10.5 m/s" rows and narrows the classification band from
14.5–16.5 (bins 14,15,16) to **14.5–15.5 m/s (bins 14,15 — bin-center
membership convention)**, and gains a 数据点数 column (sum of bin counts).
`renderSummary`'s range filter narrows to the same bins so the sentence's
per-height P90 values equal the table's. Per-height bin tables and the
multi-height chart are unchanged.

**Blocked by:** 01-unify-iec-classification (same file; sentence uses the shared classifier)

**Status:** done

## Scope

- `turbulence_summary_atom.py` `renderTable`: one row per interested height —
  `高度(m) | 风速范围 | 平均湍流强度 | 代表湍流强度(P90) | 湍流强度标准差 | 数据点数`.
  Row stats = mean of the two bin rows (existing unweighted aggregation);
  数据点数 = sum of bin `count`.
- `renderSummary`: range filter `wind_speed_bin >= 14 & <= 16` → `>= 14 & <= 15`.
- Empty-band rows render "-" as today.

## Acceptance

- [ ] Table shows exactly one band row per interested height, labeled
  "14.5-15.5 m/s", with a 数据点数 column equal to the count sum of bins 14+15
- [ ] Sentence per-height values match the table row's 代表湍流强度(P90)
- [ ] kp-202603-report regenerates: L32261 sentence reports bins-14,15 values
  (≈0.154/0.147/0.137) and classifies IEC B; table has 3 rows + 数据点数
- [ ] Per-height bin tables and multi-height chart byte-identical except image-hash lines
- [ ] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- User decision 2026-08-26: only the 14.5–15.5 row per height — ">3 m/s" and
  "9.5–10.5 m/s" rows removed from the summary table.
- Bin-center convention documented in `turbulence/spec.md` (ticket 03).
