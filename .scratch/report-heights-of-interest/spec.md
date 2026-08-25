# Feature: Report heights-of-interest config cleanup

## Intent

Every height selection visible in the report is traceable to a config field. **Recommend proposes, config decides, atoms render what they're given.** No render-time height filters, no hidden band policy inside atoms.

## Decisions (grilled 2026-08-25)

1. **`analysis_heights` splits into subsection-specific fields**: `wind_frequency_heights`, `weibull_heights`, `representative_year_heights`. Clean cutover — no alias left behind. Per-consumer interpolation policies preserved deliberately: representative_year excludes interpolated sensors; weibull / wind_frequency include them with `（内插）/（外推）` labels.
2. **New `wind_rose_heights` field** drives wind rose compute filter, tables, charts, and narrative. The hardcoded render bands (≥100m tables/charts, 125–160m narrative in `wind_rose/model/wind_rose_atom.py`, `wind_rose_grid_atom.py`, `wind_rose_power_grid_atom.py`) are removed entirely.
3. **Band-when-available discovery** for `wind_rose_heights` and `temporal_heights`: recommend emits 120–160m heights when any exist, else falls back to the unfiltered set (all WS avg for temporal; all exact WS+WD pairs for wind rose). Rationale: a 120–160-only rule produces an empty list on short masts, and both sections hard-fail on empty.
4. Wind rose pairing is exact-height WS avg + WD avg. The default pipeline (`recommend fill-heights`, default targets `125,140,160`) fills **both** WS and WD per target, so exact pairs exist at every raw + filled height in practice. Discovery must still match on pairs, not on WS alone.

## Tickets

- `issues/01-split-analysis-heights.md`
- `issues/02-wind-rose-heights.md`
- `issues/03-temporal-heights-band.md`

## Shared blast radius

All three tickets touch `configuration/model/report_config.py`, `reporting/model/analysis_parameters.py`, `reporting/api.py`, `application/usecases/generate_report.py`, and `configuration/services/recommend_report.py`. Sequencing them avoids rebase pain; if parallelized, expect conflicts in those files.

## Doc obligations

Each ticket updates the co-located spec.md files it changes the behavior of (`configuration/spec.md` for config fields + recommend rules, `reporting/spec.md` for subsection height semantics). No separate docs ticket.

## Out of scope

- vertical_profile stays config-free (all WS avg heights) — no consumer complaint on record.
- The verify-command migration lives in `.scratch/dev-tools-split/`.
