"""Per-mast 4×4 Altair scatter grid atom for representative year calibration.

Compliance: Subdomain layout | Entity | Atom Pattern
"""

from __future__ import annotations

from pathlib import Path

import altair as alt
import numpy as np
import polars as pl
import vl_convert as vlc
from typing_extensions import override
from typst_ir import TypstParagraph

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.representative_year.compute import (
    _SECTOR_NAMES,
    _find_sector,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.model.report_meta import (
    RepYearSectorAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.model.schemas import (
    RepYearSectorSchema,
)


class RepYearSectorFigureAtom(ReportAtom[RepYearSectorSchema, RepYearSectorAtomMeta]):
    """Renders per-mast 4×4 Altair scatter grid with regression lines.

    - Table: None
    - Image: 4×4 facet grid of mast_ws vs meso_ws per 16-direction sector,
      with regression lines overlaid
    - Summary: None

    The ``df`` field holds sector statistics (validated by
    ``RepYearSectorSchema``).  Raw timeseries for scatter plotting are stored
    only in ``self.meta`` (``mast_df``, ``meso_df``) — the schema never sees
    timeseries data.
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return f"{self.meta.mast_name} ({int(self.meta.height)}m) ← {self.meta.meso_name} 16方向扇区训练数据"

    @property
    @override
    def default_table_caption(self) -> str | None:
        return None

    @override
    def renderTable(self) -> None:
        """No table for this atom."""
        return None

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate 4×4 Altair facet scatter grid with regression lines.

        Joins meso and mast timeseries on nearest timestamp, assigns each
        row to a 16-point wind-direction sector, and renders a facet grid
        of mast vs meso wind speed scatter plots.
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = (
            output_dir
            / f"{self.meta.mast_name}_{self.meta.meso_name}_"
            f"{int(self.meta.height)}m_sectors_{cache_key}.png"
        )

        if not force and image_path.exists():
            return image_path

        meta = self.meta
        mast_df = meta.mast_df
        meso_df = meta.meso_df

        # ── Resolve column names ─────────────────────────────────────────
        mast_ws_col = meta.mast_ws_col
        meso_ws_col = meta.meso_ws_col
        wd_col = meta.wd_col

        # ── Build aligned dataframe ──────────────────────────────────────
        # Both pre-aligned upstream — simple inner join on timestamp
        merged = (
            mast_df.sort("timestamp")
            .rename({mast_ws_col: "mast_ws"})
            .select(["timestamp", "mast_ws"])
            .join(
                meso_df.sort("timestamp").select(["timestamp", meso_ws_col, wd_col]),
                on="timestamp",
                how="inner"
            )
        )

        merged = merged.with_columns(
            pl.col(wd_col)
            .map_elements(
                lambda x: _find_sector(x) if x is not None else 0,
                return_dtype=pl.Int32,
            )
            .alias("_sector")
        )
        merged = merged.filter(pl.col("_sector") > 0)

        # ── Vectorized per-sector R² via group_by ───────────────────────
        sector_name_map = {i + 1: name for i, name in enumerate(_SECTOR_NAMES)}

        def _r2(group: pl.DataFrame) -> float:
            x = group[meso_ws_col].to_numpy()
            y = group["mast_ws"].to_numpy()
            mask = ~(np.isnan(x) | np.isnan(y))
            x_c, y_c = x[mask], y[mask]
            if len(x_c) < 3:
                return 0.0
            slope, intercept = np.polyfit(x_c, y_c, 1)
            ss_res = float(np.sum((y_c - (slope * x_c + intercept)) ** 2))
            ss_tot = float(np.sum((y_c - np.mean(y_c)) ** 2))
            return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        r2_map: dict[int, float] = {}
        for (sector_idx,), group in merged.group_by("_sector"):
            r2_map[int(sector_idx)] = _r2(group)

        def _sector_label(idx: int) -> str:
            name = sector_name_map.get(idx, "")
            r2 = r2_map.get(idx, 0.0)
            return f"{name}(R²={r2:.2f})"

        merged = merged.with_columns(
            pl.col("_sector")
            .map_elements(lambda x: _sector_label(x), return_dtype=pl.Utf8)
            .alias("sector_name")
        )

        # ── Dynamic axis cap: max(15, 90th percentile) ──────────────────
        p90 = float(merged.select([
            pl.max_horizontal(meso_ws_col, "mast_ws").quantile(0.9)
        ]).item())
        axis_cap = max(15.0, p90)

        # ── Convert to pandas for Altair ─────────────────────────────────
        pdf = merged.select([meso_ws_col, "mast_ws", "sector_name"]).to_pandas()
        pdf.columns = ["meso_ws", "mast_ws", "sector"]
        # Altair limit is 5000 rows; sample if over
        if len(pdf) > 5000:
            pdf = pdf.sample(n=5000, random_state=42)

        # ── Build chart ──────────────────────────────────────────────────
        x_title = f"{meta.meso_name}风速 (m/s)"
        y_title = f"{meta.mast_name}风速 (m/s)"
        base = alt.Chart(pdf).encode(
            x=alt.X("meso_ws:Q", title=x_title, scale=alt.Scale(domain=[0, axis_cap])),
            y=alt.Y("mast_ws:Q", title=y_title, scale=alt.Scale(domain=[0, axis_cap])),
            tooltip=["meso_ws", "mast_ws", "sector"],
        )

        scatter = base.mark_circle(size=15, opacity=0.5)

        regression = base.mark_line(color="red", strokeWidth=2).transform_regression(
            "meso_ws", "mast_ws"
        )

        # Build sort list matching actual facet labels
        label_order = [_sector_label(i + 1) for i in range(16)]
        chart = (
            alt.layer(scatter, regression)
            .facet(
                facet=alt.Facet("sector:N", sort=label_order),
                columns=4,
                title=f"{meta.mast_name} ← {meta.meso_name} ({meta.height}m)",
            )
            .configure_axis(labelFontSize=10, titleFontSize=12)
            .configure_view(strokeWidth=0.5, stroke="#cccccc")
        )

        # ── Export via vl_convert ────────────────────────────────────────
        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """No summary for this atom."""
        return []


