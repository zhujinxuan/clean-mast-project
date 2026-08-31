# 04 — Operator contract and timerange semantics

**Type:** grilling

**Status:** ready-for-human

**Blocked by:** None

## Question

Fix the exact operator contract for all reconstruction (cross, meso, vertical — one contract):

- `fit(source × target-with-missing, config) → fit artifact`
- `predict(fit × source × timerange) → full synthetic target series`
- `fill(fit × source × observed target × timerange) → target with gaps filled (missing-only)`

Open details to decide:

1. **Partial source coverage**: predict over a timerange where the source has gaps — partial output + provenance, or hard requirement on source coverage?
2. **Back-reconstruction timerange**: the 2022–2023-mast-with-2025-target case — reconstructing outside the fit's training overlap. Is timerange a predict-time argument only, or does fit record/exploit it? How does the fit artifact represent valid prediction span?
3. **fill semantics**: exact intersection of predict output with observed gaps; how the feasibility screen's spans (ticket 09) bound what fill attempts.
4. **Where timerange comes from in config**: per reconstruction set, or global per pipeline stage?
5. **Provenance**: per-point `ReconstructionSource` (Julia merge semantics precedent) — keep, extend?

Context: memory `core://agent/4` (merge semantics, provenance mechanism already exists).

## Acceptance

- [ ] Contract signatures + semantics recorded under `## Answer`; CONTEXT.md terms updated if sharpened
- [ ] Decisions propagated to tickets 09, 10, 13 if they change those questions
- [ ] Map Decisions-so-far updated
- [ ] N/A — decision ticket, no code (verify_baseline not applicable)
