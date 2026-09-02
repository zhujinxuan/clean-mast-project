# 15 — Horizontal WD benchmark metric

**Type:** grilling

**Status:** resolved

**Blocked by:** None

## Question

Ticket 06 left the horizontal WD benchmark metric unspecified ("ε-group sort per sensor type at its own reference height"). Ticket 07 then fixed the vertical WD metric: wrapped-MAE primary, ε = 2°, computed only over timestamps with ws ≥ 3 m/s (nearest-in-height WS sensor as filter source), circular-mean bias secondary, circular RMSE as diagnostic, no speed weighting. Ticket 08 reused the same metric for the WD interpolation exam.

Decide: does `benchmark-horizontal` adopt the identical WD metric (wrapped-MAE, ε = 2°, ws ≥ 3 m/s filter, same secondary/diagnostic stack), or does horizontal WD consciously differentiate?

Consider:

1. **Filter source**: vertical uses the nearest-in-height WS sensor to the WD layer; horizontal WD reconstruction references another mast/meso — which WS field gates the metric (target-mast nearest WS? source? either?).
2. **ε = 2° at reference height**: direction-sensor accuracy ≈ noise below 2° — does that argument transfer unchanged to cross-mast/meso reconstruction, where source–target direction differences dwarf sensor noise?
3. **Speed weighting**: deferred to backlog for vertical (training complexity); the same deferral presumably applies — confirm, don't re-open.

## Answer

Decided 2026-09-02, user-confirmed (grilling + ticket 19 research):

1. **Identical stack (Q1).** `benchmark-horizontal` adopts the vertical WD metric stack: wrapped-MAE primary — mean |wrap(θ−θ̂)| on (−180°, 180°]; circular-mean bias secondary; circular RMSE + P90|bias| diagnostics; WD selected independently of WS (ticket 06's per-sensor-type sorts at own reference heights); offsets fitted as circular means, never arithmetic means of raw angles.
2. **Filter source (Q2).** The ws ≥ 3 m/s gate uses the **target-mast** WS sensor nearest in height to the reference WD sensor — both of ticket 07's justifications (vane reliability, energy content) are target-local; the source's speed is irrelevant. Timestamps with missing filter WS are excluded.
3. **ε = 5° (Q3, per ticket 19 research; amends ticket 07).** Documented vane 误差许可 runs ±2.5° (GB/T 18709-2002 §5.1.2.2) to ±5° (Met One 024A, NREL/AWS system error); field north/boom alignment dominates the uncertainty budget (legacy fleet ≈ ±3–5°); 5° envelopes sensor⊕alignment, sits above monthly-fold gap noise (~0.5–3°), and stays far below the 22.5° sector granularity at which direction is consumed. One uniform ε for both scopes — ticket 07's vertical ε = 2° is amended to 5° with the same evidence.
4. **Speed weighting (Q4).** Deferral confirmed — stays in the map's Not-yet-specified (backlog candidate if unweighted proves noisy); not re-opened.

## Acceptance

- [x] Horizontal WD metric recorded under `## Answer`
- [x] Consistent with tickets 06, 07
- [x] Map Decisions-so-far updated
- [x] N/A — decision ticket, no code (verify_baseline not applicable)

## Comments

- 2026-09-01: graduated from the map's Not-yet-specified (sharp since ticket 07 resolved; ticket 08 reused the metric for WD interpolation without challenge).

- 2026-09-02 (grilling, user decisions): **Q1/Q2/Q4 resolved** — Q1: horizontal adopts the vertical WD metric stack identically (wrapped-MAE primary, circular-mean bias secondary, circular RMSE + P90|bias| diagnostics, WD selected independently of WS, offsets fitted as circular means). Q2: the ws ≥ 3 m/s filter source is the target-mast WS sensor nearest in height to the reference WD sensor (both of ticket 07's justifications are target-local); timestamps with missing filter WS are excluded. Q4: speed weighting stays deferred (map's Not-yet-specified unchanged). **Q3 (ε value) parks on ticket 19** — user intuition: 2° may be too small; instrument 误差许可 should ground the choice.

- 2026-09-02 (ticket 19 resolved, `research/wd-epsilon.md`): **Q3 evidence landed.** Recommended ε = 5° for both scopes: documented sensor 误差许可 runs ±2.5° (GB/T 18709) to ±5° (Met One 024A, NREL/AWS system error); field alignment dominates the budget (documented 16° misalignment on a well-built mast; legacy fleet total ≈ ±3–5°); 2° is honest only with ±1°-class sensor + <1° north referencing. Research also recommends amending ticket 07's vertical ε 2° → 5° (identical truth uncertainty in both exams). Presented to the user for confirmation.
