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
_PANELS_PER_ROW = 3  # multi-x wrap width; panels never shrink to fit more


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


def _panel_label(x_label: str, y_label: str, single_x: bool) -> str:
    """Panel header: ``y ← x`` (y regressed on x); bare y when x is fixed."""
    if single_x:
        return y_label
    return f"{y_label} ← {x_label}"


def _panel_order(
    data: pd.DataFrame,
    x_labels: list[str],
    y_labels: list[str],
    single_x: bool,
) -> list[str]:
    """Facet sort order: actual pairs by (y, x) label order — reading order."""
    y_rank = {label: i for i, label in enumerate(y_labels)}
    x_rank = {label: i for i, label in enumerate(x_labels)}
    pairs = sorted(
        set(zip(data["x_label"], data["y_label"])),
        key=lambda p: (
            y_rank.get(p[1], len(y_rank)),
            x_rank.get(p[0], len(x_rank)),
            p[1],
            p[0],
        ),
    )
    return [_panel_label(x, y, single_x) for x, y in pairs]


class ScatterRegressionAtom(
    ReportAtom[ScatterPanelSchema, ScatterRegressionAtomMeta]
):
    """Renders a scatter grid with per-panel OLS regression annotations.

    - Image: compact packing — one panel per actual (x, y) pair, wrapped
      at ``_PANELS_PER_ROW`` per row in (y, x) label order (the matrix
      geometry lives in the correlation-matrix table). Multi-x panels are
      headed ``y ← x``; a single x source (2.3.7's ERA5) keeps bare
      height headers, wrapped at up to 4. Each panel: points, red OLS
      line drawn from the fitted stats, and a two-line annotation (r,
      RMSE, y = ax + b).
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

        points_pdf = self.meta.pairs_df.drop_nulls(["x", "y"]).to_pandas()
        if points_pdf.empty:
            return Path()

        chart = self._build_chart(points_pdf)
        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)
        return image_path

    def _build_chart(self, points_pdf: pd.DataFrame) -> alt.Chart:
        """Wrapped-panel chart from the complete-pair rows."""
        meta = self.meta
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
        overlay_rows = sum(len(o) for o in overlays)
        budget = _MAX_SCATTER_POINTS - overlay_rows
        if len(points_pdf) > budget:
            points_pdf = points_pdf.sample(n=budget, random_state=42)
        data = pd.concat(
            [points_pdf.assign(kind="point"), *overlays], ignore_index=True
        )

        # ── Compact packing: one wrapped panel per actual pair ─────────
        single_x = len(meta.x_labels) <= 1
        data["panel"] = [
            _panel_label(x, y, single_x)
            for x, y in zip(data["x_label"], data["y_label"])
        ]
        panel_order = _panel_order(data, meta.x_labels, meta.y_labels, single_x)

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

        # ── Wrap layout ─────────────────────────────────────────────────
        columns = (
            max(1, min(4, len(meta.y_labels))) if single_x else _PANELS_PER_ROW
        )
        chart = layered.facet(
            facet=alt.Facet("panel:N", sort=panel_order, title=""),
            columns=columns,
            title=meta.chart_title,
        )
        return (
            chart.configure_axis(labelFontSize=10, titleFontSize=12)
            .configure_header(labelFontSize=11)
            .configure_view(strokeWidth=0.5, stroke="#cccccc")
        )

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return []
