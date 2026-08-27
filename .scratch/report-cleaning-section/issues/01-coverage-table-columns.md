# 01 — 2.3.2 coverage table: difference-oriented columns

**What to build:** Redesign `CleaningCoverageAtom` columns. The current
原始占比/清洗后占比 columns carry no signal (both hug 100%); replace with the
cleaning delta. New column set (10 columns):

测风塔 | 高度(m) | 应有点数 | 原始点数 | 清洗后点数 | 清洗剔除(点) | 清洗剔除(%) | 清洗后可用率(%) | 插补后点数 | 插补后占比(%)

Definitions:
- 清洗剔除(点) = 原始点数 − 清洗后点数
- 清洗剔除(%) = 清洗剔除 ÷ 原始点数 (1 decimal; 原始为 0 → em-dash)
- 清洗后可用率(%) = 清洗后点数 ÷ 应有点数 (1 decimal)
- 插补后占比(%) unchanged (插补后 ÷ 应有)
- 原始占比 column is REMOVED (redundant: 可用率差值即剔除占比)

Missing stage input keeps the em-dash convention for its downstream columns.

**Blocked by:** None — can start immediately

**Status:** needs-triage

## Scope

- `cleaning/assemble.py::_coverage_rows` + `CleaningCoverageSchema` +
  `CleaningCoverageAtom` (model/overview_atoms.py): new fields, drop
  raw-percentage column.
- Stats sentence (`_stats_sentence`) unchanged.
- Keep the single combined table (heights-of-interest rows only; few rows per
  mast) — do NOT split per mast here; the per-mast split is ticket 02's
  concern for 2.3.3.

## Acceptance

- Generated 2.3.2 table for `projects/2026-08-27-松原查干花镇1.2GW` shows the
  10 columns above with M5057 150m row: 52560 | 51696 | 51696 | 0 | 0.0 |
  98.4 | 52560 | 100.0.
- Updated unit tests for the new row math (delta, both percentages, zero-raw
  guard).
- `uv run python scripts/verify_baseline.py --package cleanmast` is green
