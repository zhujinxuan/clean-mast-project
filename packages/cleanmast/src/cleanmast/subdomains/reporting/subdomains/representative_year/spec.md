## Purpose

Multi-mast representative year calibration analysis for wind resource reports. Produces a summary table (all masts), per-mast 16-sector statistics table, and per-mast 4×4 Altair scatter grid.

## Rules

- Inherits all rules from `reporting/spec.md` (which inherits `subdomains/spec.md`).
- `section.from_inputs` accepts `list[SingleMastAnalysisInput]` with calibration payloads.
- Per-mast figures use Altair for 4×4 sector scatter grids.

## 业务说明 (Business description)

### Domain context

代表年选取: 从多年数据中选出一个月度风速分布最接近长期平均的年份，作为后续所有评估的时间基准。"代表" 的意思是代表性，非政治性。
