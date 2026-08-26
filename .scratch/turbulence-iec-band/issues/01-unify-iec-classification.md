# 01 — Unify IEC classification: single band-membership classifier

**What to build:** One IEC classification implementation living in
`reporting/subdomains/turbulence/model/iec.py` (band-membership semantics:
rep TI above the C curve ⇒ B, above B curve ⇒ A, above A curve ⇒ A+). Today
`compute.py` carries a private duplicate of `IEC_CATEGORIES` / `compute_iec_ti`
/ `classify_iec_category`, while `turbulence_summary_atom.py` inlines a third
threshold chain with stricter semantics — that chain is why the 2.4.7 sentence
says "IEC C 类" when every per-bin row in the same report says B.

**Blocked by:** None — can start immediately

**Status:** done

## Scope

- `model/iec.py`: gain `classify_iec_category(representative_ti, wind_speed)`
  (moved verbatim from `compute.py`; strict `>` thresholds, "C" default for
  None/zero wind).
- `compute.py`: delete its private `IEC_CATEGORIES`, `compute_iec_ti`,
  `classify_iec_category`; import them from `model.iec` (compute→model is the
  sanctioned direction per `model/iec.py`'s docstring). No re-exports —
  clean cutover.
- `turbulence_summary_atom.py` `renderSummary`: replace the inline
  `ti_a_plus/ti_a/ti_b` if-chain with
  `classify_iec_category(mean_rep_ti, 15.0)`. Behavior change is INTENDED:
  classification moves from exceed-the-curve to band membership.
- `tests/reporting/turbulence/test_turbulence_compute.py`: update imports to
  source `classify_iec_category` / `compute_iec_ti` from `model.iec`.

## Acceptance

- [ ] Exactly one `classify_iec_category` / `IEC_CATEGORIES` /
  `compute_iec_ti` definition repo-wide (in `model/iec.py`)
- [ ] Summary sentence classifies with band membership: rep TI 0.1447 at
  15 m/s ⇒ "IEC B 类" (matches per-bin tables and chart bands)
- [ ] `uv run lint-imports` passes (no model→compute dependency introduced)
- [ ] Existing classifier tests pass against the new location
- [ ] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- Diagnosis 2026-08-26: per-bin table (compute.py classifier), chart bands
  (model/iec.py), and summary sentence (inline chain) were three
  implementations, two conventions. Band membership is the majority
  convention and matches IEC chart practice; the inline chain was the outlier.
