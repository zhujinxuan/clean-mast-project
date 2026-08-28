# 01 — Site-level cross-mast IEC conclusion in 2.6.5

**What to build:** A cross-mast conclusion at the END of the 五十年一遇风速总结
subsection (after the per-mast comparison + IEC class atoms), rendered for
every project:

1. **Determination table** (site level): 高度 | 跨塔最大保守持续(m/s) |
   跨塔最大保守极大(m/s) | 判定等级 — one row per height of interest.
   判定等级 from the existing `_classify_wind_class` thresholds applied to
   the cross-mast max values.
2. **Conclusion paragraph** driven by the approved rule:
   - 相差不大 (every height: sustained range < 3.0 AND extreme range < 4.2)
     → single sentence: the worst (most severe) height class across the site,
     e.g. "测风数据在标准空气密度条件下，50 年一遇最大持续风速低于 37.5 m/s，
     50 年一遇极大风速低于 52.5 m/s。根据《GB/T 18451.1-2022 风力发电机组
     设计要求》，本项目可选择 IEC III 类及以上等级的风力发电机。"
   - 相差大 → per-mast class (most severe across that mast's heights); if all
     masts agree → same single sentence; if they differ → one zoned sentence
     per mast: "M5972 测风塔代表区域机位选择 IEC X 类及以上等级的风力发电机。"
   - Any value above class I thresholds → S 类场址专用 wording.
3. Constants: `SUSTAINED_RANGE_LIMIT_MS = 3.0`,
   `EXTREME_RANGE_LIMIT_MS = 4.2` (= 3 × 1.4 nominal gust factor) in
   extreme_wind (compute or model per layer rules), docstring noting they are
   engineering heuristics, not standard values.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Scope

- `extreme_wind/compute/`: cross-mast aggregation (per-height max + range),
  site/mast classification — pure functions over the existing comparison
  results.
- `extreme_wind/model/`: new atoms — site determination table + conclusion
  paragraph (text assembled in compute/assemble, atom renders).
- `extreme_wind/section.py`: after the per-mast loop, one cross-mast pass
  appending the two atoms at the end of 2.6.5.
- Boundary strictness: "低于 37.5" means strictly below; classify at the
  boundary consistently with `_classify_wind_class` (≤ threshold → that
  class) and word the sentence with the classified tier's threshold values.

## Acceptance

- Songyuan 3-mast project regenerated: 2.6.5 ends with the determination
  table + a single-class conclusion sentence (verify the expected class from
  the rendered comparison tables).
- Synthetic fixtures prove: single-class path, zoned path (two masts
  differing ≥3 m/s sustained), agree-despite-large-range path, S-class path.
- `uv run python scripts/verify_baseline.py --package cleanmast` is green
