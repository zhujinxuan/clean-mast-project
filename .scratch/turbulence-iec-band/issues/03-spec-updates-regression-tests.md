# 03 — Turbulence spec.md + regression tests for IEC classification

**What to build:** Lock the fix in. `turbulence/spec.md` documents the two
conventions this bug violated (single classifier; band membership) plus the
bin-center band convention; regression tests pin sentence/table consistency
so a future refactor cannot reintroduce a second threshold chain.

**Blocked by:** 01-unify-iec-classification, 02-summary-table-band-count

**Status:** done

## Scope

- `reporting/subdomains/turbulence/spec.md` 业务说明 / Rules:
  - IEC classification has exactly one implementation (`model/iec.py`);
    atoms and compute MUST NOT inline threshold chains.
  - Classification semantics: band membership — rep TI between C and B
    reference curves ⇒ B (matches the IEC band chart and per-bin tables).
  - Band labels follow bin-center membership: "X.5–Y.5 m/s" = integer bins
    X..Y (14.5–15.5 ⇒ bins 14,15).
  - Summary table carries only the 14.5–15.5 m/s classification band with
    数据点数.
- `tests/reporting/turbulence/test_turbulence_atoms.py`:
  - Regression: summary sentence classifies band-membership B when per-bin
    rows classify B (synthetic df with rep TI between C and B curves).
  - Table shape: one row per height, 6 columns including 数据点数, label
    "14.5-15.5 m/s".
- Check `reporting/spec.md` turbulence line stays accurate; update if the
  capability description drifts.

## Acceptance

- [ ] spec.md records the three conventions above
- [ ] New regression test fails if the summary atom re-inlines classification
  thresholds (i.e., asserts against the shared classifier's semantics)
- [ ] New table test asserts columns/rows/数据点数 of the summary table
- [ ] `uv run python scripts/verify_baseline.py --package cleanmast` is green

## Comments

- Follows the repo rule: known divergence is a ticket, conventions live in
  spec.md — this ticket converts the 2026-08-26 diagnosis into standards.
