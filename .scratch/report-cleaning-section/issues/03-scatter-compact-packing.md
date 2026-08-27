# 03 — 2.3.5 same-tower scatter: compact panel packing, no empty matrix cells

**What to build:** `ScatterRegressionAtom` currently renders a full
x_labels × y_labels facet matrix for multi-x grids; diagonal and
lower-triangle cells render as empty framed axes (looks broken in the PDF —
see M5972 同塔 figure, 3 real panels + 6 empty boxes). Change the multi-x
layout to **compact packing**: only the actual pair panels, laid out
left-to-right in reading order (wrap at 3–4 per row), each panel titled with
its pair (`y ← x` or `x vs y` per existing annotation convention).

- The matrix view is already carried by the correlation-matrix table; the
  figure does not need matrix geometry.
- Delete the pad-rows machinery (`kind == "pad"` filler rows) once facet is
  gone — it also simplifies the Altair 5000-row budget (ticket-agnostic bugfix
  already landed; removing pads makes it simpler still).
- Single-x grids (2.3.7 meso) already pack compactly — unchanged.
- 2.3.6 cross-mast figures: same packing rule applies if they use the matrix
  path.
- **Wrapping rule (approved):** fixed 3 panels per row, pairs in
  lexicographic height order — 4 heights → 6 panels (3+3), 5 heights → 10
  panels (3+3+3+1). Never shrink panels to fit more per row; the 120px width
  is sized for the two-line annotation. Panel order stays deterministic
  height order (reproducibility), not correlation-strength order.

**Blocked by:** None — can start immediately

**Status:** done

## Scope

- `cleaning/model/scatter_regression_atom.py::renderImage`: replace facet
  matrix with wrapped compact layout; drop pad_rows; keep per-panel OLS line +
  r/RMSE/y=ax+b annotation, axis cap, and sampling budget logic.
- Altair wrapping: `columns=N` on a flat facet (or `alt.concat` hconcat/vconcat
  rows) — pick whichever matches existing sibling figure atoms.

## Acceptance

- Regenerated 2.3.5 figures for the songyuan project show exactly 3 panels
  for a 3-height mast, no empty frames; 2.3.6/2.3.7 figures unchanged in
  content.
- Existing scatter tests updated; no MaxRowsError at realistic sizes.
- `uv run python scripts/verify_baseline.py --package cleanmast` is green
