# Spec: fifty-year-conclusion

Add the site-level cross-mast IEC conclusion to 2.6.5 五十年一遇风速总结,
plus two en-passant bug fixes found during recon (Method3 sustained rows
dropped; 2.6.1 static IEC table mislabels Va as Vref).

## Approved decisions (grilling rounds 1–2, 2026-08-27/28)

- Method mapping (verified): method1=五倍平均风速法, method2=五日最大法
  (Gumbel), method3=极端风速模型法(EWM, 1.25×observed max). 保守估计列
  already exists = per-mast per-height max of the three methods
  (`build_summary_comparison`).
- **"相差不大"判据**: for EVERY height of interest, cross-mast range
  (max−min) of the conservative column < 3.0 m/s (sustained) AND < 4.2 m/s
  (extreme, = 3 × 1.4 nominal). Any layer over either limit → 相差大.
- **相差不大** → per height take the cross-mast MAX conservative values,
  classify each height (existing `_classify_wind_class`: III 37.5/52.5,
  II 42.5/59.5, I 50/70, else S), site class = most severe across heights;
  single conclusion sentence.
- **相差大** → per-mast class = most severe across that mast's heights; if
  all masts share the class → single conclusion; if classes differ → zoned
  sentences per mast ("Mxxx 测风塔代表区域机位选择 IEC X 类及以上等级").
- Presentation: conclusion paragraph + one site-level determination table
  (高度 | 跨塔最大保守持续 | 跨塔最大保守极大 | 判定等级).
- S class wording (any value above I thresholds): S 类场址专用 phrasing.
- Boundary wording strict: 低于 X / 不低于 X aligned with the threshold table.
- Citation: conclusion cites 《GB/T 18451.1-2022 风力发电机组 设计要求》
  (identical adoption of IEC 61400-1); the static reference table keeps its
  IEC 61400-1 label.
- Thresholds 3.0 / 4.2 hardcoded as named constants in extreme_wind (NOT
  config-driven); 4.2 = 3 × 1.4 nominal, decoupled from per-height gust
  factors.
- Bug fixes in scope: Method3 sustained rows + empty narrative; 2.6.1 static
  table corrected to IEC names — Vref (10-min sustained reference)
  50/42.5/37.5, Ve50 (50-yr extreme gust) 70/59.5/52.5, S 场址专用 (the
  handwritten table's Ve50/Vref labels are swapped vs the standard; follow
  the standard's names with the handwritten values).

## Architecture notes (from recon)

- `ExtremeWindSection.from_inputs` receives ALL masts at once but computes
  per mast in a loop; the conclusion needs a post-loop cross-mast pass.
- Per-mast comparison/IEC atoms and classification logic already exist —
  reuse `_classify_wind_class` and `build_summary_comparison` outputs.
- Tickets: issues/01 (conclusion), 02 (method3 sustained), 03 (IEC table).
  All independent.
