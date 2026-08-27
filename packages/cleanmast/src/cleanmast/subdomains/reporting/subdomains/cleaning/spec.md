## Purpose

数据清洗与插补 reporting capability — subsections 2.3.2–2.3.7 of section 2.3.
Documents the cleaning pipeline stages so the report can state what was done
to the data before wind-resource analysis.

## Rules

- Inherits all rules from `reporting/spec.md` (which inherits
  `subdomains/spec.md`).
- The Julia pipeline (process-clean → tower-shading → reconstruct-meso) is
  the executor. This capability is a READ-ONLY consumer of its outputs;
  it never re-cleans or re-authors data.
- Heights come from `MastRef.cleaning_heights` ONLY (WS avg sensor heights,
  band-when-available 120–160m, discovered by
  `_discover_cleaning_heights` in recommend_report). No subsection derives
  its own heights.
- The expected-points denominator for coverage statistics is the mast's
  rep-year `analysis_window` (a `TimeRange`) on the inclusive 10-minute
  interval grid — see `compute/coverage.py`.
- 16-sector binning for tower-shading statistics uses the shared
  `reporting/model/sectors.py` (`find_sector`, 1-indexed, clockwise from N);
  this capability MUST NOT re-implement the binning formula.
- Wording rules: Chinese, engineer report style (工程报告文体), concise
  statements of what was done and how much data was affected. No quality
  judgement (不评价数据质量好坏), no marketing language.
- Wave 1: every section renders a one-line placeholder text atom. Wave 2
  replaces the `from_inputs` bodies with real compute → assemble pipelines.

## Section input contract (Wave 2)

Each section's `from_inputs(items: list[SingleMastAnalysisInput])` receives
one item per mast of the `cleaning_pipeline` dataset:

- `item.time_series` — the reconstruct-meso parquet (FINAL pipeline stage)
  clipped to the rep-year analysis window.
- `item.mast_name`, `item.parameters` — as for every capability.
- `item.cleaning_payload: CleaningAnalysisPayload | None` — non-None for
  cleaning-dataset masts. Fields:
  - `raw_input` / `clean_input` / `tower_shading_input` —
    `TimeSeriesSource | None` with project-relative paths from
    process-clean.toml (input/output) and tower-shading.toml (output).
    `tower_shading_input` is None when the mast has no tower-shading entry.
  - `raw_series` / `clean_series` / `tower_shading_series` —
    `TimeSeriesData | None`: the same stages ALREADY LOADED and clipped to
    `analysis_window` by `generate_report.load_datasets` (boundary loads;
    sections MUST NOT load parquet). None mirrors the corresponding
    `*_input`. An empty clip is NOT an error — a stage with no data in the
    rep-year window is itself reportable (2.3 coverage subject matter).
  - `cleaning_heights: list[float]` — the only heights source.
  - `analysis_window: TimeRange` — rep-year window; expected-points
    denominator.
- `item.representative_year_calibration_payload` — set for cleaning masts
  wired to a meso source in representative-year.toml (recommend mirrors the
  repyear meso wiring); 2.3.7 中尺度插补 reads its `meso_time_series`.

Stage data flow: `raw_series` → (process-clean) → `clean_series` →
(tower-shading) → `tower_shading_series` → (reconstruct-meso) →
`item.time_series`.

## Anti-patterns

- Loading parquet inside sections — loading happens at the
  `generate_report.load_datasets` boundary.
- Height discovery inside this capability — heights are config-driven.
- A second sector-binning formula.

## 业务说明 (Business description)

### Domain context

数据清洗与插补说明数据在风资源分析前的处理过程: 哪些规则剔除了
不合理数据、塔影效应如何合并邻近高度、缺失时段如何用同塔/异塔/
中尺度数据插补。

### Key concepts

- 2.3.2 数据清洗与插补总体概况: 各塔各阶段数据量与覆盖率汇总。
- 2.3.3 缺测与不合理数据处理: 清洗规则及各规则触发的数据点数。
- 2.3.4 塔影效应处理: 邻近高度风速合并 (±2m) 及分扇区统计。
- 2.3.5 同塔插补: 同塔其他高度/传感器的回归插补。
- 2.3.6 异塔插补: 相邻测风塔间的回归插补。
- 2.3.7 中尺度插补: 中尺度再分析数据 (ERA5) 驱动的重建插补。

### Business constraints

- 覆盖率是可信度指标: 每个阶段的覆盖率必须可追溯到期望点数。
- 插补方法与参数必须如实报告，不得暗示数据质量结论。
