# 2026-08-27 — 2.3.2 coverage table: wind-speed caption + 传感器类型 column

**What to build:** The 2.3.2 coverage table only ever lists 风速(均值) sensors
(cleaning_heights are WS-avg by discovery rule), but nothing says so:

1. Caption: "数据清洗与插补各阶段数据点统计表" →
   "各塔主测风层风速数据清洗与插补各阶段数据点统计表" (state 风速).
2. New column 传感器类型 after 高度(m), rendered from SensorColumn metadata as
   `{类型}({统计})` — e.g. `风速(均值)` — reusing
   `SENSOR_TYPE_TRANSLATIONS`/`STAT_TYPE_TRANSLATIONS` from
   `cleaning/model/constants.py`. Fallback `风速(均值)` is NOT hardcoded:
   resolve the sensor at (mast, height) from the stage series metadata;
   em-dash when no sensor matches.

New column set (11): 测风塔 | 高度(m) | 传感器类型 | 应有点数 | 原始点数 |
清洗后点数 | 清洗剔除(点) | 清洗剔除(%) | 清洗后可用率(%) | 插补后点数 |
插补后占比(%)

**Blocked by:** None — can start immediately

**Status:** done

## Scope

- `cleaning/model/overview_atoms.py`: caption + header/column insertion.
- `cleaning/assemble.py::_coverage_rows` (or wherever rows gain fields):
  per-row sensor-type label resolved from stage sensor metadata.
- `tests/reporting/cleaning/test_cleaning_overview.py`: caption, column
  position, label rendering, fallback.

## Acceptance

- Songyuan + kp regenerated reports show the 11-column table with
  `风速(均值)` rows and the 风速 caption.
- `uv run python scripts/verify_baseline.py --package cleanmast` is green
