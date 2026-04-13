"""Monthly wind pattern atom for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path

import altair as alt
import polars as pl
import vl_convert as vlc
from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.types import (
    TypstParagraph,
    TypstTable,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
    get_height_display_name,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TemporalPatternSchema,
)


@dataclass
class SingleMastMonthlyPatternAtom(ReportAtom[TemporalPatternSchema, SingleMastMeta]):
    """Renders 12-month monthly wind speed pattern for a single mast.

    - Table: Month-by-month wind speed by height (12 rows x heights columns)
    - Image: Grouped bar chart showing average wind speed by month
    - Summary: Chinese description of seasonal pattern characteristics
    """

    @property
    def default_image_caption(self) -> str:
        return f"{self.meta.mast_name} 月风速变化图"

    @property
    def default_table_caption(self) -> str:
        return f"{self.meta.mast_name} 月风速变化表"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render as TypstTable IR node with monthly wind speed by height.

        Rows: 12 months (1-12)
        Columns: 月份 | 各高度平均风速...
        """
        # Get unique heights and their display names (sorted)
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_cols = []
        for row in heights_df.iter_rows(named=True):
            display = get_height_display_name(row["height"], row["interpolation_marker"])
            height_cols.append((row["height"], display))

        # Aggregate by month and height (mean of mean_speed)
        monthly = (
            self.df.group_by(["month", "height", "interpolation_marker"])
            .agg([
                pl.col("mean_speed").mean().alias("avg_monthly_speed"),
            ])
            .sort(["month", "height"])
        )

        # Build the table rows (12 months)
        rows = []
        for month in range(1, 13):
            month_data = monthly.filter(pl.col("month") == month)

            cells = [f"{month}月"]
            for height, _ in height_cols:
                speed_row = month_data.filter(pl.col("height") == height)
                if speed_row.height > 0:
                    speed = speed_row.row(0, named=True)["avg_monthly_speed"]
                    speed_val = speed if speed is not None else 0
                    cells.append(f"{speed_val:.2f}")
                else:
                    cells.append("-")
            rows.append(cells)

        avg_cells = ["平均"]
        for col_idx in range(1, len(height_cols) + 1):
            values = []
            for row in rows:
                cell = row[col_idx]
                if cell != "-":
                    values.append(float(cell))
            if values:
                avg_cells.append(f"{sum(values) / len(values):.2f}")
            else:
                avg_cells.append("-")
        rows.insert(0, avg_cells)

        # Build header: month + one column per height
        headers = ["月份"] + [display for _, display in height_cols]

        return TypstTable(headers=headers, data=rows, caption=self._resolve_table_caption())

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate 12-month monthly pattern grouped bar chart with >=100m heights only.

        Uses Altair grouped bar chart, exports to PNG via vl-convert.
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"monthly_pattern_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Aggregate by month and height (mean of mean_speed)
        monthly_df = (
            self.df.group_by(["month", "height", "interpolation_marker"])
            .agg([
                pl.col("mean_speed").mean().alias("avg_speed"),
            ])
            .sort(["month", "height"])
        )

        # Filter to >=100m heights for visualization and valid speeds
        plot_df = monthly_df.filter(
            (pl.col("height") >= 100) & (pl.col("avg_speed").is_not_null())
        )

        # Add display name for legend
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(x["height"], x["interpolation_marker"])
            )
            .alias("height_display")
        )
        plot_df = plot_df.sort(["month", "height"], descending=[False, True])

        # Convert to pandas for Altair compatibility
        plot_df_pd = plot_df.to_pandas()
        _PALETTE = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
            "#9467bd", "#8c564b", "#e377c2", "#bcbd22",
            "#17becf", "#aec7e8",
        ]
        height_display_order = (
            plot_df.select(["height", "height_display"])
            .unique()
            .sort("height", descending=True)["height_display"]
            .to_list()
        )
        color_range = [_PALETTE[i % len(_PALETTE)] for i in range(len(height_display_order))]

        # Create Altair grouped bar chart
        bars = alt.Chart(plot_df_pd).mark_bar().encode(
            x=alt.X(
                "month:O",
                title="月份",
                scale=alt.Scale(domain=list(range(1, 13))),
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "avg_speed:Q",
                title="平均风速(m/s)",
                scale=alt.Scale(zero=False),
            ),
            color=alt.Color(
                "height_display:N",
                title="高度",
                legend=alt.Legend(orient="right"),
                scale=alt.Scale(domain=height_display_order, range=color_range),
            ),
            xOffset=alt.XOffset(
                "height_display:N",
                sort=alt.EncodingSortField(field="height", op="mean", order="descending"),
            ),
            tooltip=["month", "height_display", alt.Tooltip("avg_speed:Q", format=".2f")],
        )

        chart = bars.properties(
            title=f"{self.meta.mast_name} 月平均风速分布",
            width=700,
            height=400,
        ).interactive()

        # Export to PNG
        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """Generate simplified Chinese summary when all heights agree on peak/min months."""
        # Aggregate by month and height
        monthly_df = (
            self.df.group_by(["month", "height", "interpolation_marker"])
            .agg([
                pl.col("mean_speed").mean().alias("avg_speed"),
            ])
            .sort(["month", "height"])
        )

        high_df = monthly_df.filter(
            (pl.col("height") >= 100) & (pl.col("avg_speed").is_not_null())
        )

        if high_df.height == 0:
            return []

        height_stats = []
        for h in high_df["height"].unique().sort():
            h_df = high_df.filter(pl.col("height") == h)

            annual_avg = h_df["avg_speed"].mean()
            max_row = h_df.sort("avg_speed", descending=True).row(0, named=True)
            min_row = h_df.sort("avg_speed", descending=False).row(0, named=True)

            display = get_height_display_name(h)
            height_stats.append({
                "display": display,
                "annual_avg": annual_avg,
                "max_month": max_row["month"],
                "min_month": min_row["month"],
            })

        if len(height_stats) == 0:
            return []

        max_months = {s["max_month"] for s in height_stats}
        min_months = {s["min_month"] for s in height_stats}

        max_agrees = len(max_months) == 1
        min_agrees = len(min_months) == 1

        if not max_agrees and not min_agrees:
            return []

        height_parts = "、".join(s["display"] for s in height_stats)
        avg_parts = "、".join(f"{s['annual_avg']:.2f}m/s" for s in height_stats)

        sentences = [f"{self.meta.mast_name}测风塔 {height_parts} 高度月平均风速 {avg_parts}"]

        if max_agrees:
            sentences.append(f"最大值都出现在 {height_stats[0]['max_month']} 月")
        if min_agrees:
            sentences.append(f"最小值都出现在 {height_stats[0]['min_month']} 月")

        summary = "，".join(sentences) + "。"
        return [TypstParagraph(text=summary)]
