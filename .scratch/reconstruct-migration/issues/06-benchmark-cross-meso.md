# 06 — Benchmark protocol: cross and meso selection

**Type:** grilling

**Status:** ready-for-human

**Blocked by:** None

## Question

Finalize the cross/meso source-and-method selection benchmark beyond the charted baseline (ticket 01: ≥1yr & ≥90% availability → whole-series WS RMSE; otherwise monthly blocked bootstrap, ≥5 folds, exam = 1 month; ε-group sort with ε=0.05 m/s, bias secondary, power RMSE only with configured reference curve, coverage tertiary).

Open details:

1. **Heights of interest for the ≥90% availability rule**: which heights count — config analysis heights, all WS/WD heights of interest, per-mast? Where is this defined?
2. **Fallback chain**: meso sources grouped by dataset (ERA5/MERRA2) → ranked within group → primary + fallback chain (fixes Julia's single-meso-no-fallback hole). Is mixed-source fallback (different meso datasets in one chain) acceptable? Provenance mechanism already exists.
3. **Cross-mast priority score**: Julia uses 0.6·corr + 0.2·dir + 0.2·coverage to pre-rank ordered mast pairs. Keep as a screening pre-rank, or replace with benchmark-derived ranking entirely?
4. **Fallback chain ranking**: same ε-group sort as primary selection, or simpler (availability-weighted)?
5. **Benchmark evidence persistence**: what is kept — fold metrics table, winner summary, per-fold fits (charted: discarded)? Where does it surface — recommend output artifact, report section?

Context: memory `core://agent/4` (O(n²) sources, Julia priority score, merge semantics). Research ticket 02 may sharpen metric choices.

## Acceptance

- [ ] Full protocol recorded under `## Answer`, implementable without further decisions
- [ ] Interactions with tickets 09 (screen) and 11 (reference height) consistent
- [ ] Map Decisions-so-far updated
- [ ] N/A — decision ticket, no code (verify_baseline not applicable)

## Comments

- 2026-08-31 research (ticket 02, `research/mcp-benchmarking.md`): the charted ≥90% availability gate is stricter than gap-impact evidence requires — FGW 80% is a documented option. Decide whether the gate is config (default 90%, 80% option) rather than fixed.
- 2026-08-31 research (ticket 03, `research/shear-validation.md`): Quick-2025 cautions on RMSE-based selection — read the flagged tension before locking the ε-group sort's primary metric.
