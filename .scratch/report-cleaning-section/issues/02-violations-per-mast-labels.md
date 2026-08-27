# 02 — 2.3.3 violations: per-mast tables, Chinese sensor labels, drop summary sentences

**What to build:** Rework the violations exhibit in `CleaningRulesSection`:

1. **One table per mast** instead of a single all-mast table (the combined
   table is unreadably long). One `CleaningViolationsAtom` per mast with
   caption `{mast} 分规则剔除点数统计`; the 测风塔 column disappears.
2. **Chinese structured sensor labels** instead of raw column names, built
   from `SensorColumn` metadata (never regex the column string):
   `{height}m {类型}({方向}, {统计})` — e.g. `WindSpeed_70m_ESE_avg [m/s]` →
   `70m 风速(ESE, 均值)`; merged/absent direction → omit the direction slot
   (`140m 风速(均值)`). Fall back to the raw column name when no matching
   sensor metadata exists. Sensor source: payload.clean_series.sensors,
   fallback raw_series.sensors. 统计 mapping: avg→均值, sd→标准差, max→极大值
   (extend SENSOR_TYPE_TRANSLATIONS-style constants in model/constants.py).
3. **Row ordering**: sensor type (风速 → 风向 → 温度 → 气压 → 其他), then
   height ascending, then rule name. Current render order is YAML order
   (70m/30m/30m/50m… — looks random).
4. **Remove the per-mast summary sentences** ("M5057：检验共剔除6968点，占检验期
   总点数的5.11%。…") — the per-mast totals are subsumed by the per-mast
   tables. Keep the missing-YAML note per mast (剔除统计从略) as a one-line
   placeholder paragraph for that mast.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Scope

- `cleaning/assemble.py::build_cleaning_rules_atoms`: emit one violations
  atom per mast; row labeling + ordering; drop `_violation_sentence` and the
  `summary_lines` meta (check `CleaningViolationsAtomMeta` consumers).
- `cleaning/model/constants.py`: add stat-type and label-building helper
  (`format_sensor_label(sensor) -> str`).
- Section `from_inputs` must thread per-mast sensors through (payload stage
  series) into the assemble call.
- The rules table (CleaningRulesAtom) is unchanged.

## Acceptance

- Regenerated 2.3.3 for the songyuan 3-mast project shows three captioned
  per-mast tables, labeled rows (`150m 风向(N, 均值)` style), sorted as
  specified, and no summary-sentence paragraph.
- Unit tests: label formatting (with/without direction, unknown stat),
  ordering, per-mast atom split, missing-metadata fallback.
- `uv run python scripts/verify_baseline.py --package cleanmast` is green
