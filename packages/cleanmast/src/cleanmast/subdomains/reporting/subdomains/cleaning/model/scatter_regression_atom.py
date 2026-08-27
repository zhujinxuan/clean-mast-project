"""Scatter grid with OLS regression line and annotation atom (2.3.5–2.3.7)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import altair as alt
import numpy as np
import pandas as pd
import vl_convert as vlc
from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.cleaning.model.report_meta import (
    ScatterRegressionAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model.schemas import (
    ScatterPanelSchema,
)

_MAX_SCATTER_POINTS = 5000  # Altair limit; sample beyond, keep regression exact


def annotation_lines(
    slope: float | None,
    intercept: float | None,
    r: float | None,
    rmse: float | None,
) -> list[str]:
    """Two-line per-panel annotation: ``r``/RMSE and the fitted equation.

    Numbers only — no quality judgement wording.
    """
    if slope is None or intercept is None:
        return []
    line1_parts: list[str] = []
    if r is not None:
        line1_parts.append(f"r={r:.3f}")
    if rmse is not None:
        line1_parts.append(f"RMSE={rmse:.2f}m/s")
    return [
        "  ".join(line1_parts),
        f"y={slope:.2f}x{intercept:+.2f}",
    ]


def _axis_cap(values: np.ndarray) -> float:
    """Shared scatter axis cap: max(15, 90th percentile) — sibling rule."""
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return 15.0
    return max(15.0, float(np.percentile(finite, 90)))


class ScatterRegressionAtom(
    ReportAtom[ScatterPanelSchema, ScatterRegressionAtomMeta]
):
    """Renders a scatter grid with per-panel OLS regression annotations.

    - Image: panels laid out by ``meta.x_labels`` / ``meta.y_labels`` —
      a matrix grid for multi-x sources (upper-triangle pairs leave the
      lower/diagonal cells empty), a single row of height panels for a
      single x source (2.3.7). Each panel: points, red OLS line drawn
      from the fitted stats, and a two-line annotation (r, RMSE,
      y = ax + b).
    - Table: none
    - Summary: none

    The validated ``df`` holds per-panel stats; raw scatter points live in
    ``meta.pairs_df`` (timeseries data never enters the schema — same
    convention as the representative-year figure atom).
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return self.meta.caption

    @override
    def renderTable(self) -> TypstTable | None:
        """No table for this atom."""
        return None

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"{self.meta.slug}_{cache_key}.png"
        if not force and image_path.exists():
            return image_path

        meta = self.meta
        points_pdf = (
            meta.pairs_df.drop_nulls(["x", "y"]).to_pandas()
        )
        if points_pdf.empty:
            return Path()

        cap = _axis_cap(
            np.concatenate(
                [points_pdf["x"].to_numpy(), points_pdf["y"].to_numpy()]
            )
        )

        # ── Per-panel overlays derived from the fitted stats ────────────
        stats_rows: list[dict[str, Any]] = self.df.to_pandas().to_dict(
            orient="records"
        )
        overlays: list[pd.DataFrame] = []
        for row in stats_rows:
            for text_line, y_anchor in zip(
                annotation_lines(row["slope"], row["intercept"], row["r"], row["rmse"]),
                (cap * 0.96, cap * 0.87),
            ):
                overlays.append(
                    pd.DataFrame(
                        {
                            "x_label": [row["x_label"]],
                            "y_label": [row["y_label"]],
                            "kind": ["text"],
                            "x": [cap * 0.05],
                            "y": [y_anchor],
                            "label": [text_line],
                        }
                    )
                )
            overlays.append(
                pd.DataFrame(
                    {
                        "x_label": [row["x_label"], row["x_label"]],
                        "y_label": [row["y_label"], row["y_label"]],
                        "kind": ["line", "line"],
                        "x": [0.0, cap],
                        "y": [
                            float(row["intercept"]),
                            float(row["slope"]) * cap + float(row["intercept"]),
                        ],
                        "label": [None, None],
                    }
                )
            )
        # Vega-Lite derives the facet domain from the data — pad the grid
        # with empty combos so skipped panels (upper-triangle matrix,
        # unregressable panels) keep their place as empty cells.
        panel_labels = set(zip(points_pdf["x_label"], points_pdf["y_label"]))
        panel_labels |= {(o["x_label"][0], o["y_label"][0]) for o in overlays}
        pad_rows = [
            {"x_label": x, "y_label": y, "kind": "pad", "x": None, "y": None, "label": None}
            for x in meta.x_labels
            for y in meta.y_labels
            if (x, y) not in panel_labels
        ]
        overlay_rows = sum(len(o) for o in overlays)
        budget = _MAX_SCATTER_POINTS - overlay_rows - len(pad_rows)
        if len(points_pdf) > budget:
            points_pdf = points_pdf.sample(n=budget, random_state=42)
        data = pd.concat(
            [points_pdf.assign(kind="point"), *overlays], ignore_index=True
        )
        if pad_rows:
            data = pd.concat([data, pd.DataFrame(pad_rows)], ignore_index=True)

        # ── Layers from one shared source ───────────────────────────────
        base = alt.Chart(data)
        scatter = (
            base.transform_filter("datum.kind == 'point'")
            .mark_circle(size=15, opacity=0.5)
            .encode(
                x=alt.X(
                    "x:Q",
                    title="风速 (m/s)",
                    scale=alt.Scale(domain=[0, cap]),
                ),
                y=alt.Y(
                    "y:Q",
                    title="风速 (m/s)",
                    scale=alt.Scale(domain=[0, cap]),
                ),
                tooltip=["x_label", "y_label", "x", "y"],
            )
        )
        regression = (
            base.transform_filter("datum.kind == 'line'")
            .mark_line(color="red", strokeWidth=2)
            .encode(x="x:Q", y="y:Q")
        )
        annotation = (
            base.transform_filter("datum.kind == 'text'")
            .mark_text(align="left", baseline="top", fontSize=9)
            .encode(x="x:Q", y="y:Q", text="label:N")
        )
        layered = alt.layer(scatter, regression, annotation).properties(
            width=120, height=110
        )

        # ── Grid layout ─────────────────────────────────────────────────
        if len(meta.x_labels) > 1:
            chart = layered.facet(
                row=alt.Row("y_label:N", sort=meta.y_labels, title=""),
                column=alt.Column("x_label:N", sort=meta.x_labels, title=""),
                title=meta.chart_title,
            )
        else:
            chart = layered.facet(
                column=alt.Column("y_label:N", sort=meta.y_labels, title=""),
                columns=max(1, min(4, len(meta.y_labels))),
                title=meta.chart_title,
            )
        chart = (
            chart.configure_axis(labelFontSize=10, titleFontSize=12)
            .configure_header(labelFontSize=11)
            .configure_view(strokeWidth=0.5, stroke="#cccccc")
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)
        return image_path

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return []
