"""Daily wind pattern atom for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path

import altair as alt
import polars as pl
import vl_convert as vlc
from typing_extensions import override

from cleanmast.subdomains.assessment.shared.protocols.report_atom import ReportAtom
from cleanmast.subdomains.assessment.shared.ir_types import (
    TypstParagraph,
    TypstTable,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
    get_height_display_name,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.value_objects.schemas import (
    TemporalPatternSchema,
)


@dataclass
class SingleMastDailyPatternAtom(ReportAtom[TemporalPatternSchema, SingleMastMeta]):
    """Renders 24-hour daily wind speed pattern for a single mast.

    - Table: Hour-by-hour wind speed by height (24 rows x heights columns)
    - Image: Multi-line chart showing average wind speed by hour
    - Summary: Chinese description of daily pattern characteristics
    """

    @property
    def default_image_caption(self) -> str:
        return f"{self.meta.mast_name} 日风速变化图"

    @property
    def default_table_caption(self) -> str:
        return f"{self.meta.mast_name} 日风速变化表"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render as TypstTable IR node with hourly wind speed by height.

        Rows: 24 hours (0-23)
        Columns: 小时 | 各高度平均风速...
        """
        # Get unique heights and their display names (sorted)
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_cols = []
        for row in heights_df.iter_rows(named=True):
            display = get_height_display_name(row["height"], row["interpolation_marker"])
            height_cols.append((row["height"], display))

        # Aggregate by hour and height (mean of mean_speed across all days)
        hourly = (
            self.df.group_by(["hour", "height", "interpolation_marker"])
            .agg([
                pl.col("mean_speed").mean().alias("avg_hourly_speed"),
            ])
            .sort(["hour", "height"])
        )

        # Build the table rows (24 hours)
        rows = []
        for hour in range(24):
            hour_data = hourly.filter(pl.col("hour") == hour)
            
            cells = [f"{hour:02d}:00"]
            for height, _ in height_cols:
                speed_row = hour_data.filter(pl.col("height") == height)
                if speed_row.height > 0:
                    speed = speed_row.row(0, named=True)["avg_hourly_speed"]
                    speed_val = speed if speed is not None else 0
                    cells.append(f"{speed_val:.2f}")
                else:
                    cells.append("-")
            rows.append(cells)

        # Build header: hour + one column per height
        headers = ["小时"] + [display for _, display in height_cols]

        return TypstTable(headers=headers, data=rows, caption=self.default_table_caption)

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate 24-hour daily pattern line chart with >=100m heights only.

        Uses Altair line chart with points at each hour, exports to PNG via vl-convert.
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"daily_pattern_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Aggregate by hour and height (mean of mean_speed)
        hourly_df = (
            self.df.group_by(["hour", "height", "interpolation_marker"])
            .agg([
                pl.col("mean_speed").mean().alias("avg_speed"),
            ])
            .sort(["hour", "height"])
        )

        # Filter to >=100m heights for visualization and valid speeds
        plot_df = hourly_df.filter(
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

        # Convert to pandas for Altair compatibility
        plot_df_pd = plot_df.to_pandas()

        # Create Altair multi-line chart with points
        lines = alt.Chart(plot_df_pd).mark_line(opacity=0.7, point=True).encode(
            x=alt.X(
                "hour:O",
                title="小时",
                scale=alt.Scale(domain=list(range(24))),
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
            ),
            tooltip=["hour", "height_display", alt.Tooltip("avg_speed:Q", format=".2f")],
        )

        chart = lines.properties(
            title=f"{self.meta.mast_name} 日变化风速曲线",
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
        """Generate simplified Chinese summary when all heights agree on peak/min hours."""
        # Aggregate by hour and height
        hourly_df = (
            self.df.group_by(["hour", "height", "interpolation_marker"])
            .agg([
                pl.col("mean_speed").mean().alias("avg_speed"),
            ])
            .sort(["hour", "height"])
        )

        high_df = hourly_df.filter(
            (pl.col("height") >= 100) & (pl.col("avg_speed").is_not_null())
        )

        if high_df.height == 0:
            return []

        height_stats = []
        for h in high_df["height"].unique().sort():
            h_df = high_df.filter(pl.col("height") == h)
            max_row = h_df.sort("avg_speed", descending=True).row(0, named=True)
            min_row = h_df.sort("avg_speed", descending=False).row(0, named=True)

            display = get_height_display_name(h)
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

        summary = f"{self.meta.mast_name}测风塔 {height_parts} 高度日平均风速" + "，".join(parts) + "。"
        return [TypstParagraph(text=summary)]
