# Spec docs review — full findings

Reviewed 2026-08-10 by 4 parallel reviewers against the writing-for-agents rubric (negation steering, duplication, environment caches, no-ops, unverifiable wishes, co-location, stale/sediment, format, leading words). Code claims spot-verified against `packages/cleanmast/src` and `.importlinter`.

## Cross-cutting

- **Boilerplate triplication**: all 9 reporting leaf specs copy pipeline-stage / compute-purity / frozen=True / sibling-import / when-in-doubt blocks from `reporting/spec.md` + `subdomains/spec.md`. Copies have already drifted (wind_frequency grew a clause; leaves drop the `# mutable:` escape hatch; vertical_profile invents a "section" stage).
- **Orphan lint line**: "`Any`, `# type: ignore`, `str(path)`, bare `except:`." is cloned verbatim into all 9 leaves; NO parent contains it. 9 copies, zero source of truth.
- **Two heading skeletons**: `## Code rules` wrapper (application, dataprocessing) vs flat `## Purpose / ## Rules / ## Anti-patterns / ## When in doubt` (the rest). Decision 2026-08-10: flat 5-section everywhere (Purpose / Rules / Anti-patterns / When in doubt / 业务说明).
- **Genuinely good** (the model to follow): capability-specific rules — SECTOR_COUNT (wind_rose), Polars vectorization (wind_frequency), IEC constants (turbulence); vertical_profile's Business constraints; dataprocessing overall.

## subdomains/spec.md (81 lines)

- [HIGH] Rules 9–12 (capabilities, section.py, render_subsection_content) are reporting-only but inherited by dataprocessing/configuration → move to reporting/spec.md.
- [HIGH] Lines 15–18: capability path `subdomains/{capability}/` wrong — real: `reporting/subdomains/{capability}/section.py`.
- [MEDIUM] Line 8 rule 2 "never sideways" contradicted by rule 10's render exception (lines 18–20) → qualify rule 2.
- [MEDIUM] Line 14 "use a single file when content fits one file" — unverifiable, no bound.
- [LOW] Line 47 "keep compute pure math" — "pure math" not checkable (minor).
- [LOW] Line 81 (业务说明) restates `DEFAULT_FILL_HEIGHTS = "125,140,160"` code default → keep business fact, drop code-default claim.

## reporting/spec.md (70 lines)

- [HIGH] Rules 2/4/5/6 (lines 8–12) restate parent rules 1/3/7/(4+5) verbatim despite rule 1 declaring inheritance → delete.
- [MEDIUM] Rule 8 (lines 16–17) is a weakened restatement of parent rule 12 (drops "Manual atom iteration forbidden") → delete.
- [MEDIUM] Rule 3 (line 9) enumerates 9 capabilities; duplicated again in 业务说明 lines 55–64; `ls` confesses it → drop from rule.
- [MEDIUM] Anti-patterns/when-in-doubt (lines 32–43) duplicate parent lines 47/50/58; line 37 "Stateful calculators; prefer pure functions" also duplicated in dataprocessing line 26 → delete copies.
- [MEDIUM] Line 37 "prefer pure functions" — unverifiable wish.
- [LOW] Rule 10 (lines 20–22): "never in a drift-log" names deleted machinery → "tracked only as a ticket under .scratch/".
- [LOW] Rule 7 (lines 13–15): only air_density reads `parameters.air_density` — make it an example, not a universal.
- Note: `reporting/anti-pattern.md` sits beside the spec (self-declared closed 2026-07-26) — sediment, archive or delete.

## Leaf specs (9 files)

Shared: boilerplate blocks (rules lines ~7–10, anti-patterns ~14–19, when-in-doubt ~21–25) duplicated from parents → strip; leaf keeps Purpose + capability-specific rules + 业务说明.

- **wind_rose** — [MEDIUM] rule 11 + anti-pattern 19 state magic-number rule twice (keep rule, it carries the positive).
- **weibull** — [HIGH] line 11 names ghost class `WeibullFitter`; real API is module-level `fit_weibull` (compute.py:166) → name the real API. [MEDIUM] line 34 mixes code-WHAT (ghost name included) into 业务说明 Key concepts → keep only k-parameter semantics.
- **turbulence** — [MEDIUM] statelessness ruled 3× (lines 11, 12, 20) → keep 12 + anti-pattern, drop 11. [MEDIUM] line 35 code-WHAT in 业务说明. [LOW] line 31 lists A/B/C but code also returns "A+" (compute.py:29,117).
- **wind_frequency** — [HIGH] boilerplate copy already drifted (line 8 extra clause) — proof the copies can't be maintained. [LOW] no Business constraints subsection.
- **wind_temporal** — [HIGH] zero capability-specific rules; entire normative body is no-op parent restatement → cut to Purpose + 业务说明， or add real temporal rules. [LOW] no Business constraints.
- **vertical_profile** — [MEDIUM] boilerplate with drifted vocabulary ("section" stage); frozen rule drops escape hatch. Business constraints = best content in the set.
- **extreme_wind** — [HIGH] line 3 claims complete Gumbel coverage; max-sensor fit missing (ticket `.scratch/reporting-extreme-wind-gumbel/issues/01-extreme-sensor-gumbel-fit.md`) → qualify + reference ticket. [HIGH] line 19 anti-pattern contradicts line 11 Path()-sentinel rule → rewrite positively or delete. [MEDIUM] line 25 "NoMast" ghost; real mechanism `IECStandardsAtomMeta` `mast_name="_no_mast"` (model/report_meta.py:17). [MEDIUM] line 31 says 年最大值序列; code fits 5-day maxima (extract_five_day_maxima, 五日最大法). [LOW] line 11 "not None" half is type-enforced; hoist sentinel convention to reporting/spec.md.
- **representative_year** — [MEDIUM] line 12 restates Purpose (4×4 grid); line 11 restates reporting rule 7. [LOW] line 32 "非政治性" clarification is a no-op. [LOW] minimal 业务说明.
- **air_density** — [MEDIUM] entire rules body is boilerplate; only Purpose + 业务说明 are unique. [LOW] no Business constraints.

## shared/spec.md (36 lines)

- [HIGH] Line 6 admission list names modules that don't exist (path utils, atmospheric constants); omits config-model modules that do (fill_height_config.py etc.) → rewrite admission rule to match the real bar.
- [MEDIUM] Entry bar stated 3× (lines 5, 15, 22) → keep line 5.
- [MEDIUM] Lines 26–29 redefine timeseries concepts owned by shared/timeseries/spec.md → pointer.
- [LOW] Lines 7–8 bare prohibitions without positive admission target.

## shared/timeseries/spec.md (45 lines)

- [HIGH] Lines 14–16 falsely claim configuration services route through the repository protocol; actually config TOML goes through `services/config_io.py` raw tomli. Contradicts configuration/spec.md:23.
- [MEDIUM] Lines 7–13 duplicate subdomains/spec.md rule 13 routing → keep detail here (this file owns the protocol), pointer in parent.
- [LOW] Lines 8–9 enumerate helper names from io/validation.py → drop enumeration.

## dataprocessing/spec.md (75 lines)

- [HIGH] Line 8 claims inheritance but lines 18–19 (services/__init__.py exports public symbols) contradict parent rule 7 (api.py sole interface; no api.py exists) → state the exception explicitly here.
- [MEDIUM] Lines 22–23 repository-access anti-pattern duplicated in configuration/spec.md:25 → belongs here only (constrains dataprocessing's imports).
- [MEDIUM] Shear-reuse business fact (lines 54–55) duplicated in configuration/spec.md:53–54 → keep here, pointer there.
- [LOW] Line 26 "prefer pure functions" — unverifiable wish → hard rule with escape hatch or drop.
- Format: drop `## Code rules` wrapper → flat 5-section.

## configuration/spec.md (61 lines)

- [HIGH] Line 23 "tomli imported ONLY in services/config_io.py" is false — infrastructure/file_repository.py:20–21 also imports tomli/tomli_w; the `tomli-configuration-gateway-only` contract whitelists both → name both gateways or delegate to the contract.
- [MEDIUM] Line 22 polices imports of the deleted `old_configuration` module → dead rule, delete.
- [LOW] Line 55 describes future `meso-models/` directory → drop until it lands.

## application/spec.md (21 lines)

- [HIGH] Too thin: 3 of 5 real usecases are config-driven (recommend/train/execute fill-heights) but the spec never mentions ProjectConfig, discover_*_config() vs load_config(), save_*_model(), bootstrap injection. The train-workflow pattern lives in subdomains/spec.md:36–40 (sprawl) → move it here and add config-driven usecase rules.
- [MEDIUM] TimeSeriesData-boundary rule stated in 3 files (here + subdomains:29–30 + dataprocessing:9–12) → dataprocessing owns the enforceable side; others become pointers.
- [LOW] Only spec with no 业务说明; `## Code rules` wrapper → flat 5-section + business section.
