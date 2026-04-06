"""Daily power pattern atom for single mast analysis.

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
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
    get_height_display_name,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TemporalPatternSchema,
)


@dataclass
class SingleMastDailyPowerPatternAtom(ReportAtom[TemporalPatternSchema, SingleMastMeta]):
    """Renders 24-hour daily wind power density pattern for a single mast.

    - Table: Hour-by-hour power density by height (24 rows x heights columns)
    - Image: Multi-line chart showing average power density by hour
    - Summary: Chinese description of daily power pattern characteristics
    """

    @override
    def renderTable(self) -> str:
        """Render as Typst table with hourly power density by height.

        Rows: 24 hours (0-23)
        Columns: 小时 | 各高度平均风功率密度...
        """
        # Get unique heights and their display names (sorted)
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_cols = []
        for row in heights_df.iter_rows(named=True):
            display = get_height_display_name(row["height"], row["interpolation_marker"])
            height_cols.append((row["height"], display))

        # Aggregate by hour and height (mean of mean_power across all days)
        hourly = (
            self.df.group_by(["hour", "height", "interpolation_marker"])
            .agg([
                pl.col("mean_power").mean().alias("avg_hourly_power"),
            ])
            .sort(["hour", "height"])
        )

        # Build the table rows (24 hours)
        rows = []
        for hour in range(24):
            hour_data = hourly.filter(pl.col("hour") == hour)
            
            cells = [f"  [{hour:02d}:00]"]
            for height, _ in height_cols:
                power_row = hour_data.filter(pl.col("height") == height)
                if power_row.height > 0:
                    power = power_row.row(0, named=True)["avg_hourly_power"]
                    power_val = power if power is not None else 0
                    cells.append(f"[{power_val:.1f}]")
                else:
                    cells.append("[-]")
            rows.append(", ".join(cells) + ",")

        # Build header: hour + one column per height
        header_cells = "[小时], " + ", ".join([f"[{display}(W/m²)]" for _, display in height_cols])

        # Build column spec
        col_spec = "auto, " + ", ".join(["auto"] * len(height_cols))

        return f"""#table(
  columns: ({col_spec}),
  inset: 8pt,
  align: center,
  table.header(
    {header_cells}
  ),
{chr(10).join(rows)}
)
"""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate 24-hour daily power pattern line chart with >=100m heights only.

        Uses Altair line chart with points at each hour, exports to PNG via vl-convert.
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"daily_power_pattern_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Aggregate by hour and height (mean of mean_power)
        hourly_df = (
            self.df.group_by(["hour", "height", "interpolation_marker"])
            .agg([
                pl.col("mean_power").mean().alias("avg_power"),
            ])
            .sort(["hour", "height"])
        )

        # Filter to >=100m heights for visualization and valid power values
        plot_df = hourly_df.filter(
            (pl.col("height") >= 100) & (pl.col("avg_power").is_not_null())
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

        # Export to PNG
        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> str:
        """Generate Chinese summary of daily wind power density pattern."""
        # Aggregate by hour and height
        hourly_df = (
            self.df.group_by(["hour", "height", "interpolation_marker"])
            .agg([
                pl.col("mean_power").mean().alias("avg_power"),
            ])
            .sort(["hour", "height"])
        )

        # Filter to >=100m heights
        high_df = hourly_df.filter(
            (pl.col("height") >= 100) & (pl.col("avg_power").is_not_null())
        )

        # Get unique heights for mention
        heights = (
            high_df.select(["height", "interpolation_marker"])
            .unique()
            .sort("height")
        )
        height_strs = [
            get_height_display_name(row["height"], row["interpolation_marker"])
            for row in heights.iter_rows(named=True)
        ]

        if high_df.height > 0:
            # Find peak and minimum hours across all heights
            by_hour = (
                high_df.group_by("hour")
                .agg([
                    pl.col("avg_power").mean().alias("overall_avg"),
                ])
                .sort("hour")
            )
            
            peak_hour = by_hour.sort("overall_avg", descending=True).row(0, named=True)
            min_hour = by_hour.sort("overall_avg", descending=False).row(0, named=True)

            # Calculate overall daily average
            daily_avg = high_df["avg_power"].mean()
            daily_max = high_df["avg_power"].max()
            daily_min = high_df["avg_power"].min()

            # Find which height has strongest/weakest daily variation
            variation_stats = (
                high_df.group_by(["height", "interpolation_marker"])
                .agg([
                    pl.col("avg_power").max().alias("max_power"),
                    pl.col("avg_power").min().alias("min_power"),
                ])
                .with_columns(
                    (pl.col("max_power") - pl.col("min_power")).alias("variation")
                )
                .sort("variation", descending=True)
            )
            
            most_variable = variation_stats.row(0, named=True)
            most_var_str = get_height_display_name(
                most_variable["height"], most_variable["interpolation_marker"]
            )

            return (
                f"{self.meta.mast_name}测风塔日变化风功率密度分析。"
                f"分析高度包括{', '.join(height_strs)}。"
                f"日平均风功率密度{daily_avg:.1f}W/m²，"
                f"全天最高风功率密度{daily_max:.1f}W/m²，"
                f"全天最低风功率密度{daily_min:.1f}W/m²。"
                f"风功率密度峰值出现在{peak_hour['hour']:02d}:00({peak_hour['overall_avg']:.1f}W/m²)，"
                f"风功率密度低谷出现在{min_hour['hour']:02d}:00({min_hour['overall_avg']:.1f}W/m²)，"
                f"呈现典型的日变化规律。"
                f"{most_var_str}日变化幅度最大({most_variable['variation']:.1f}W/m²)，"
                f"展现了风功率密度随时间变化的动态特征。"
            )
        else:
            return (
                f"{self.meta.mast_name}测风塔日变化风功率密度分析。"
                f"分析高度包括{', '.join(height_strs)}。"
                f"暂无有效风功率密度数据。"
            )
