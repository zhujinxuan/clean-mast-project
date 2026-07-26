"""Monthly wind power pattern atom for single mast analysis."""

from pathlib import Path
from typing import cast

import altair as alt
import polars as pl
import vl_convert as vlc
from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.model import get_height_display_name
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.report_meta import (
    WindTemporalAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.schemas import (
    TemporalPatternSchema,
)


class SingleMastMonthlyPowerPatternAtom(ReportAtom[TemporalPatternSchema, WindTemporalAtomMeta]):
    """Renders 12-month monthly wind power density pattern for a single mast.

    - Table: Month-by-month wind power density by height (12 rows x heights columns)
    - Image: Grouped bar chart showing average wind power density by month
    - Summary: Chinese description of seasonal power pattern characteristics
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return f"{self.meta.mast_name} 月风功率密度变化图"

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} 月风功率密度变化表"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render as TypstTable IR node with monthly wind power density by height."""
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_cols = []
        for row in heights_df.iter_rows(named=True):
            display = get_height_display_name(row["height"], row["interpolation_marker"])
            height_cols.append((row["height"], display))

        monthly = (
            self.df.group_by(["month", "height", "interpolation_marker"])
            .agg([pl.col("mean_power").mean().alias("avg_monthly_power")])
            .sort(["month", "height"])
        )

        rows = []
        for month in range(1, 13):
            month_data = monthly.filter(pl.col("month") == month)
            cells = [f"{month}月"]
            for height, _ in height_cols:
                power_row = month_data.filter(pl.col("height") == height)
                if power_row.height > 0:
                    power = power_row.row(0, named=True)["avg_monthly_power"]
                    power_val = power if power is not None else 0
                    cells.append(f"{power_val:.1f}")
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
                avg_cells.append(f"{sum(values) / len(values):.1f}")
            else:
                avg_cells.append("-")
        rows.insert(0, avg_cells)

        headers = ["月份"] + [display for _, display in height_cols]
        return TypstTable(headers=headers, data=rows, caption=self.default_table_caption)

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate 12-month monthly power pattern grouped bar chart."""
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"monthly_power_pattern_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        monthly_df = (
            self.df.group_by(["month", "height", "interpolation_marker"])
            .agg([pl.col("mean_power").mean().alias("avg_power")])
            .sort(["month", "height"])
        )

        plot_df = monthly_df.filter(pl.col("avg_power").is_not_null())

        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(x["height"], x["interpolation_marker"])
            )
            .alias("height_display")
        )
        plot_df = plot_df.sort(["month", "height"], descending=[False, True])

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

        bars = alt.Chart(plot_df_pd).mark_bar().encode(
            x=alt.X(
                "month:O",
                title="月份",
                scale=alt.Scale(domain=list(range(1, 13))),
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "avg_power:Q",
                title="平均风功率密度(W/m²)",
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
            tooltip=["month", "height_display", alt.Tooltip("avg_power:Q", format=".1f")],
        )

        chart = bars.properties(
            title=f"{self.meta.mast_name} 月平均风功率密度分布",
            width=700,
            height=400,
        ).interactive()

        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """Generate simplified Chinese summary when all heights agree on peak/min months."""
        monthly_df = (
            self.df.group_by(["month", "height", "interpolation_marker"])
            .agg([pl.col("mean_power").mean().alias("avg_power")])
            .sort(["month", "height"])
        )

        high_df = monthly_df.filter(pl.col("avg_power").is_not_null())

        if high_df.height == 0:
            return []

        height_stats = []
        for h in high_df["height"].unique().sort():
            h_df = high_df.filter(pl.col("height") == h)
            annual_avg = h_df["avg_power"].mean()
            max_row = h_df.sort("avg_power", descending=True).row(0, named=True)
            min_row = h_df.sort("avg_power", descending=False).row(0, named=True)

            display = get_height_display_name(cast(float, h))
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
        avg_parts = "、".join(f"{s['annual_avg']:.1f}W/m²" for s in height_stats)

        sentences = [f"{self.meta.mast_name}测风塔 {height_parts} 高度月平均风功率密度 {avg_parts}"]

        if max_agrees:
            sentences.append(f"最大值都出现在 {height_stats[0]['max_month']} 月")
        if min_agrees:
            sentences.append(f"最小值都出现在 {height_stats[0]['min_month']} 月")

        summary = "，".join(sentences) + "。"
        return [TypstParagraph(text=summary)]
