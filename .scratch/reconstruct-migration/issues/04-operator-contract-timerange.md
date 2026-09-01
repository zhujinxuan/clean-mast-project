# 04 — Operator contract and timerange semantics

**Type:** grilling

**Status:** resolved

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

## Answer

Decided 2026-08-31 (grilling round, user-confirmed). Facts from scout: `TimeRange` IR exists (`shared/timeseries/time_range.py`, frozen min/max) and is used per-mast in meso/rep-year configs as an output grid, never a training span; Julia provenance is a write-only per-point sidecar CSV with hardcoded `reference_name="meso"`; today's fill-heights fit artifacts are write-only (`discover_fill_height_models` has zero consumers; execute embeds copied parameters — contradicting `configuration/spec.md`).

1. **Predict emits a partial series** under partial source coverage: where source data is missing the prediction is missing (flagged); never hard-fail, never fabricate.
2. **Mast entity = one contiguous observation span.** Two raw files → two entities, automatically (1:1, data decides; a single file with a large internal gap splits at ingest under the same rule). No naming convention is assumed or required. No "site" concept in the reconstruction contract — sibling stitching is report-side. The fit artifact records its training overlap; predicting outside it is allowed, flagged `extrapolated-in-time`. Cache-key timerange element = training overlap only; predict/fill windows are per-call.
3. **Fill = strict intersection**: fills a gap only where target missing ∧ prediction exists ∧ (timestamp, sensor) inside the screen's fillable spans. Never overwrites observed. Unfeasible cells are skipped without computing. User-forced pairs are allowed, flagged `screen-override`.
4. **Timeranges**: per-mast working window per phase (not per-pair — the screen makes a wider window cost-free). The reconstruct-meso window is explicitly chosen — a deliberately "long enough" subset of meso availability — and is independent of report and wt-timeseries windows. The rep-year window is coverage-driven: align all masts to the best common window when every mast has ≥90% clean-data availability there, else per-mast best-coverage; just-override for exceptions; validation: rep-year window within the reconstructed extent. How `recommend` proposes the meso window length → ticket 13.
5. **Provenance** (replaces Julia's dead sidecar CSV): (a) append-only flag columns `{sensor}_flags` in the parquet — grammar: origin flag first (`observed`|`missing`, never removed), then phase flags appended in fixed pipeline order (`clean` < `single` < `cross` < `meso` < `rep-year`), colon-joined (e.g. `observed:clean:cross:rep-year`); flags minted by the clean-stage writer (additive output-schema change; cleaning logic untouched), each later phase appends; append-only enforced by a writer API that only exposes append. (b) A per-run provenance manifest (TOML beside the output): per sensor, spans → {method, source, fit key, in/out-of-overlap, override flags} — the audit layer for "benchmark recommends, config decides".
6. **Config carries strategy identity** (method id + refs + cache key); parameters live only in the fit artifact. Working agreement: spec.md changes land before code.
7. **Two reference modes**: identity reference (default; the only mode `recommend` emits) and explicit-artifact mode (direct fit TOML path + column mapping for ad-hoc cross-pair transfer via just-override; flagged `fit-transferred`; never benchmark-recommended).

**Known drift this contract resolves**: fill-heights' write-only fit artifacts and parameter-embedding configs (spec-vs-code contradiction in `configuration/spec.md`) are replaced by identity reference + train-on-demand.
