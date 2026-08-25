# 01 — Split analysis_heights into subsection-specific fields

**What to build:** Replace the shared `analysis_heights` field with three subsection-specific fields: `wind_frequency_heights`, `weibull_heights`, `representative_year_heights`. The generic name hides a 3-consumer field; each subsection should name its own heights of interest.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Scope

- `configuration/model/report_config.py`: remove `MastRef.analysis_heights`; add the three new fields (same `list[float]`, default empty).
- `reporting/model/analysis_parameters.py`: same split on `AnalysisParameters`.
- `reporting/api.py`, `application/usecases/generate_report.py`: plumb the three fields through.
- `configuration/services/recommend_report.py`: populate all three from the existing `_discover_analysis_heights` rule (WS avg, 120–160m). Rename the discover function to match the band concept (e.g. `_discover_hub_band_heights`) since it now serves three named fields.
- Section guards in `wind_frequency/section.py`, `weibull/section.py`, `representative_year/section.py`: read their own field; keep the hard-fail-on-empty + "regenerate with `cleanmast recommend`" message pattern.
- Clean cutover: no `analysis_heights` alias, no deprecated shim, every caller migrated.

## Preserve deliberately

- `representative_year/compute.py` excludes interpolated sensors (`detect_interpolation_marker() == ""`); weibull and wind_frequency include interpolated heights with `（内插）/（外推）` labels. These policies differ on purpose — do not unify them in this ticket.

## Acceptance

- [ ] `analysis_heights` no longer exists anywhere in `packages/` (grep-clean)
- [ ] The three sections consume their own field; guards fail with the correct field name in the message
- [ ] Recommend emits the three fields with today's 120–160 WS avg rule
- [ ] kp-202603-report verify passes with a regenerated config
- [ ] `configuration/spec.md` documents the three fields and the discovery rule
- [ ] Tests updated; new coverage only where the split changes observable behavior (guard messages, config round-trip)
- [ ] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- Decided 2026-08-25 (grilling round, see `.scratch/report-heights-of-interest/spec.md`): split confirmed, clean cutover, interpolation policies preserved per consumer.
- Shared blast radius with tickets 02 and 03 — see spec.md.
