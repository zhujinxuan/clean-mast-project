# 04 — 2.3.4 no-dual-channel wording: state the verified fact precisely

**What to build:** When no mast has dual-channel heights, the section renders
`TOWER_SHADING_METHOD_TEXT_NO_TABLE` ending with "各测风塔主测风层均为单通道，无
塔影修正前后对比。" Verified against the songyuan 3-mast parquets (2026-08-27):
every mast is single-channel at **every** height, and tower-shading produced
zero merged columns — so the sentence understates the fact (主测风层 → 全部高度)
and "无塔影修正前后对比" is confusing (there was no correction at all, not just
no comparison).

Reword the no-table variant to state the actual outcome, e.g.:
"经检验，各测风塔各高度层均为单通道风速传感器，不涉及塔影修正。"
(检测范围 = all WS-avg heights, not only cleaning_heights — the detection
already scans the full sensor list, so the sentence may say 各高度层.)

Keep the method sentence + NB/T 31147-2018 citation + display equation (they
document the pipeline's behavior when dual channels exist; the project simply
has none).

**Blocked by:** None — can start immediately

**Status:** done

## Scope

- `cleaning/model/tower_shading_method_atom.py`:
  `TOWER_SHADING_METHOD_TEXT_NO_TABLE` rewording.
- If the detection currently filters to cleaning_heights before deciding
  "no dual channels", make the wording decision use the unfiltered scan
  (verify `find_dual_channel_heights` usage in assemble.py) — the sentence
  claims 各高度层, so the check must cover them.

## Acceptance

- Regenerated 2.3.4 for the songyuan project shows the new sentence; a
  synthetic dual-channel project still gets the comparison tables and the
  original text.
- Unit test for both text variants.
- `uv run python scripts/verify_baseline.py --package cleanmast` is green
