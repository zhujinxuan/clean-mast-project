# 01 — Weibull subsection: single intro sentence, drop per-mast summary paragraphs

**What to build:** The Weibull section currently renders one summary paragraph
PER MAST ("M5057测风塔在125m, 140m, 150m, 160m高度的Weibull拟合结果显示，平均
形状参数k=2.21，平均尺度参数c=8.02m/s，各高度风速分布符合Weibull分布特征，可用于
风资源评估。"). Replace with ONE intro sentence for the whole subsection,
handwritten-report style:

"对各测风塔年数据进行分析，得到各高度 Weibull 拟合结果，如下图表所示。"

Delete the per-mast paragraphs entirely — the average k/c duplicate the
parameter tables, and "符合Weibull分布特征，可用于风资源评估" is a judgement
claim, against the report's no-judgement rule.

Parameter tables (per mast) and distribution-fit figures (per mast) are
UNCHANGED. The same section code renders under both 2.4 测风年 and 2.5 代表年 —
both change (approved).

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Scope

- `reporting/subdomains/weibull/` (section.py / assemble.py / model/): find
  where the per-mast summary sentence is built (mentions 平均形状参数); remove
  it and its supporting code cleanly (no dead helpers), add the single intro
  sentence as the subsection's only paragraph.
- Tests: update/weave out per-mast summary assertions; assert the single
  intro sentence and that tables/figures still render per mast.

## Acceptance

- Regenerated reports (kp + songyuan): Weibull subsection opens with the
  single sentence; no per-mast paragraph; per-mast tables and figures intact.
- `uv run python scripts/verify_baseline.py --package cleanmast` is green
