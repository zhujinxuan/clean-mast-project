"""Daily power pattern atom for single mast analysis.

Compliance: Subdomain layout | Entity | Atom Pattern
"""

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


class SingleMastDailyPowerPatternAtom(ReportAtom[TemporalPatternSchema, WindTemporalAtomMeta]):
    """Renders 24-hour daily wind power density pattern for a single mast.

    - Table: Hour-by-hour power density by height (24 rows x heights columns)
    - Image: Multi-line chart showing average power density by hour
    - Summary: Chinese description of daily power pattern characteristics
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return f"{self.meta.mast_name} 日风功率密度变化图"

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} 日风功率密度变化表"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render as TypstTable IR node with hourly power density by height."""
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_cols = []
        for row in heights_df.iter_rows(named=True):
            display = get_height_display_name(row["height"], row["interpolation_marker"])
            height_cols.append((row["height"], display))

        hourly = (
            self.df.group_by(["hour", "height", "interpolation_marker"])
            .agg([pl.col("mean_power").mean().alias("avg_hourly_power")])
            .sort(["hour", "height"])
        )

        rows = []
        for hour in range(24):
            hour_data = hourly.filter(pl.col("hour") == hour)
            cells = [f"{hour:02d}:00"]
            for height, _ in height_cols:
                power_row = hour_data.filter(pl.col("height") == height)
                if power_row.height > 0:
                    power = power_row.row(0, named=True)["avg_hourly_power"]
                    power_val = power if power is not None else 0
                    cells.append(f"{power_val:.1f}")
                else:
                    cells.append("-")
            rows.append(cells)

        headers = ["小时"] + [display for _, display in height_cols]
        return TypstTable(headers=headers, data=rows, caption=self.default_table_caption)

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate 24-hour daily power pattern line chart with >=100m heights only."""
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"daily_power_pattern_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        hourly_df = (
            self.df.group_by(["hour", "height", "interpolation_marker"])
            .agg([pl.col("mean_power").mean().alias("avg_power")])
            .sort(["hour", "height"])
        )

        plot_df = hourly_df.filter(
            (pl.col("height") >= 100) & (pl.col("avg_power").is_not_null())
        )

        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(x["height"], x["interpolation_marker"])
            )
            .alias("height_display")
        )

        plot_df_pd = plot_df.to_pandas()

        lines = alt.Chart(plot_df_pd).mark_line(opacity=0.7, point=True).encode(
            x=alt.X(
                "hour:O",
                title="小时",
                scale=alt.Scale(domain=list(range(24))),
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
            ),
            tooltip=["hour", "height_display", alt.Tooltip("avg_power:Q", format=".1f")],
        )

        chart = lines.properties(
            title=f"{self.meta.mast_name} 日变化风功率密度曲线",
            width=700,
            height=400,
        ).interactive()

        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """Generate simplified Chinese summary when all heights agree on peak/min hours."""
        hourly_df = (
            self.df.group_by(["hour", "height", "interpolation_marker"])
            .agg([pl.col("mean_power").mean().alias("avg_power")])
            .sort(["hour", "height"])
        )

        high_df = hourly_df.filter(
            (pl.col("height") >= 100) & (pl.col("avg_power").is_not_null())
        )

        if high_df.height == 0:
            return []

        height_stats = []
        for h in high_df["height"].unique().sort():
            h_df = high_df.filter(pl.col("height") == h)
            max_row = h_df.sort("avg_power", descending=True).row(0, named=True)
            min_row = h_df.sort("avg_power", descending=False).row(0, named=True)

            display = get_height_display_name(cast(float, h))
            height_stats.append({
                "display": display,
                "max_hour": max_row["hour"],
                "min_hour": min_row["hour"],
            })

        if len(height_stats) == 0:
            return []

        max_hours = {s["max_hour"] for s in height_stats}
        min_hours = {s["min_hour"] for s in height_stats}

        max_agrees = len(max_hours) == 1
        min_agrees = len(min_hours) == 1

        if not max_agrees and not min_agrees:
            return []

        height_parts = "、".join(s["display"] for s in height_stats)

        parts: list[str] = []
        if max_agrees:
            parts.append(f"最大值都出现在 {height_stats[0]['max_hour']:02d} 时")
        if min_agrees:
            parts.append(f"最小值都出现在 {height_stats[0]['min_hour']:02d} 时")

        if not parts:
            return []

        summary = (
            f"{self.meta.mast_name}测风塔 {height_parts} 高度日平均风功率密度"
            + "，".join(parts)
            + "。"
        )
        return [TypstParagraph(text=summary)]
