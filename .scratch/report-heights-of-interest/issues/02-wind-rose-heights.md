# 02 — Config-driven wind_rose_heights, remove render-time bands

**What to build:** Add a `wind_rose_heights` config field and make the wind rose subsection fully config-driven. Today the atoms silently re-filter at render time (tables/charts ≥100m, narrative 125–160m, hardcoded in `wind_rose/model/`), which is why the kp report shows "selected heights" with no config to explain them.

**Blocked by:** None — can start immediately (shared files with 01/03, see spec.md)

**Status:** done

## Scope

- `configuration/model/report_config.py` + `reporting/model/analysis_parameters.py`: new `wind_rose_heights: list[float]` field.
- `configuration/services/recommend_report.py`: new discovery — heights with an **exact** WS avg + WD avg pair, band-when-available: 120–160m if any pair exists there, else all paired heights. (Pairing, not WS alone: a WS height without WD is silently dropped by `calculate_wind_rose` today, so recommending unpaired heights would configure a no-op.)
- `wind_rose/section.py`: guard like its siblings (hard-fail on empty with the `cleanmast recommend` message); filter the computed WindRoseSchema frame to configured heights before building atoms.
- `wind_rose/model/wind_rose_atom.py`, `wind_rose_grid_atom.py`, `wind_rose_power_grid_atom.py`: remove the `height >= 100` filters (3 sites) and the `125 <= height <= 160` narrative filters (2 sites). Atoms render whatever the frame contains.
- Update the chart captions that say 各高度（100m 以上）.

## Preserve deliberately

- Exact-height WS/WD pairing in `calculate_wind_rose` stays (no nearest-height matching) — but the silent drop should surface: log a warning naming each WS height skipped for lack of a WD pair.
- Interpolated heights stay included with `（内插）/（外推）` labels.

## Acceptance

- [ ] No height literal (`100`, `125`, `160`) remains as a render filter in `wind_rose/`; grep-clean
- [ ] `wind_rose_heights` flows config → AnalysisParameters → section → atoms; empty list hard-fails with the field-named message
- [ ] Recommend emits the field with band-when-available pair discovery
- [ ] Skipped unpaired WS heights produce a warning, not silence
- [ ] kp-202603-report verify passes; wind rose tables/charts/narrative show exactly the configured heights
- [ ] `reporting/spec.md` wind_rose entry documents the config-driven heights and the pairing rule
- [ ] Tests: atoms render unfiltered frames; section filters to config; recommend discovery covers band + fallback + unpaired cases
- [ ] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- Decided 2026-08-25 (grilling round): single field drives compute + tables + charts + narrative; band-when-available (120–160 with fallback to all pairs). Narrative will cover more heights than today when config is wide — accepted; users trim in config.
- Fact basis: default fill-heights (`recommend fill-heights`, default `125,140,160`) fills both WS and WD per target, so exact pairs exist at every raw + filled height in the standard pipeline.
