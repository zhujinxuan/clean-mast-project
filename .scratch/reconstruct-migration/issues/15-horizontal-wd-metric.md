# 15 — Horizontal WD benchmark metric

**Type:** grilling

**Status:** ready-for-human

**Blocked by:** None

## Question

Ticket 06 left the horizontal WD benchmark metric unspecified ("ε-group sort per sensor type at its own reference height"). Ticket 07 then fixed the vertical WD metric: wrapped-MAE primary, ε = 2°, computed only over timestamps with ws ≥ 3 m/s (nearest-in-height WS sensor as filter source), circular-mean bias secondary, circular RMSE as diagnostic, no speed weighting. Ticket 08 reused the same metric for the WD interpolation exam.

Decide: does `benchmark-horizontal` adopt the identical WD metric (wrapped-MAE, ε = 2°, ws ≥ 3 m/s filter, same secondary/diagnostic stack), or does horizontal WD consciously differentiate?

Consider:

1. **Filter source**: vertical uses the nearest-in-height WS sensor to the WD layer; horizontal WD reconstruction references another mast/meso — which WS field gates the metric (target-mast nearest WS? source? either?).
2. **ε = 2° at reference height**: direction-sensor accuracy ≈ noise below 2° — does that argument transfer unchanged to cross-mast/meso reconstruction, where source–target direction differences dwarf sensor noise?
3. **Speed weighting**: deferred to backlog for vertical (training complexity); the same deferral presumably applies — confirm, don't re-open.

## Acceptance

- [ ] Horizontal WD metric recorded under `## Answer`
- [ ] Consistent with tickets 06, 07
- [ ] Map Decisions-so-far updated
- [ ] N/A — decision ticket, no code (verify_baseline not applicable)

## Comments

- 2026-09-01: graduated from the map's Not-yet-specified (sharp since ticket 07 resolved; ticket 08 reused the metric for WD interpolation without challenge).
