# 11 — Reference-height selection (O(n²) kill)

**Type:** grilling

**Status:** ready-for-human

**Blocked by:** None

## Question

Finalize the O(n²) kill: selection-stage screening runs at reference height only; the winner gets a full-height final fit.

Decide:

1. **Reference height choice**: per-mast highest WS vs configured (e.g. 160m) vs hybrid (configured, fallback to highest)? Open since 2026-08-28.
2. **Selection cost bound**: confirm all (source × method) candidates fit at reference height only during selection; full-height training happens once, for the winner. Any exception (height-dependent methods)?
3. **Height disagreement**: if the winning source/method at reference height plausibly differs at other heights — accept (simplicity) or add per-height selection as an escape hatch?
4. **Cross-mast pre-screening**: Julia's all-ordered-pairs × all-sensors blowup — what pre-filters apply before benchmarking (distance? availability? priority score from ticket 06)?

Context: memory `core://agent/4` records the O(n²) sources (`RecommendTrainMesoCommand` all masts × mesos × 3 methods; redundant full-alignment for one correlation; all ordered mast×mast pairs).

## Acceptance

- [ ] Reference-height rule + cost bound recorded under `## Answer`
- [ ] Consistent with ticket 06 benchmark protocol
- [ ] Map Decisions-so-far updated
- [ ] N/A — decision ticket, no code (verify_baseline not applicable)
