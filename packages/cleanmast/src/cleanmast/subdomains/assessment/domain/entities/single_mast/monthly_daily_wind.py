"""Monthly daily wind pattern atom for 3x4 grid visualization.

ADR-GUARDRAILS: ddd-t-001-aggregates, ddd-t-002-entities-value-objects, ddd-t-003-report-atoms
Compliance: Aggregate ✓ | Entity ✓ | Content-Addressable ✓
"""

from dataclasses import dataclass
from pathlib import Path

import altair as alt
import polars as pl
from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
    get_height_display_name,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TemporalPatternSchema,
)

# Month names for display
_MONTH_NAMES = {
    1: "1月",
    2: "2月",
    3: "3月",
    4: "4月",
    5: "5月",
    6: "6月",
    7: "7月",
    8: "8月",
    9: "9月",
    10: "10月",
    11: "11月",
    12: "12月",
}


@dataclass
class SingleMastMonthlyDailyWindAtom(ReportAtom[TemporalPatternSchema, SingleMastMeta]):
    """Renders 3x4 grid of daily wind patterns for each month.

    - Table: Summary table of monthly wind statistics
    - Image: 3x4 grid of line charts (Jan-Dec), each showing 24-hour pattern
    - Summary: Chinese description of daily wind patterns
    """

    @override
    def renderTable(self) -> str:
        """Render summary table of monthly wind statistics.

        Shows each month with its average wind speed and diurnal range.
        """
        # Calculate monthly statistics (using mean_speed which analyzer produces)
        monthly_stats = (
            self.df.group_by("month")
            .agg([
                pl.col("mean_speed").mean().alias("avg_speed"),
                pl.col("mean_speed").max().alias("max_speed"),
                pl.col("mean_speed").min().alias("min_speed"),
                (pl.col("mean_speed").max() - pl.col("mean_speed").min()).alias("diurnal_range"),
            ])
            .sort("month")
        )

        rows = []
        for row in monthly_stats.iter_rows(named=True):
            month_name = _MONTH_NAMES.get(row["month"], f"{row['month']}月")
            rows.append(
                f'  [{month_name}], [{row["avg_speed"]:.2f}], '
                f'[{row["max_speed"]:.2f}], [{row["min_speed"]:.2f}], '
                f'[{row["diurnal_range"]:.2f}],'
            )

        return f"""#table(
  columns: (auto, auto, auto, auto, auto),
  inset: 8pt,
  align: center,
  table.header(
    [月份], [平均风速(m/s)], [最大风速(m/s)], [最小风速(m/s)], [日较差(m/s)]
  ),
{chr(10).join(rows)}
)
"""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate 3x4 grid of monthly daily wind patterns.

        Creates a faceted chart with 12 subplots (3 rows x 4 columns),
        one for each month. Each subplot shows the 24-hour wind speed pattern.

        Args:
            output_dir: Directory to save the PNG file
            force: If True, regenerate even if cached file exists

        Returns:
            Path to the generated PNG file
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"monthly_daily_wind_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Filter to >=100m heights for visualization
        plot_df = self.df.filter(pl.col("height") >= 100)

        # Add month name for faceting
        plot_df = plot_df.with_columns(
            pl.col("month").map_elements(
                lambda m: _MONTH_NAMES.get(m, f"{m}月"),
                return_dtype=pl.String,
            ).alias("month_name")
        )

        # Add display name for legend
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(x["height"], x.get("interpolation_marker", "")),
                return_dtype=pl.String,
            )
            .alias("height_display")
        )

        # Calculate hourly averages for smoother curves
        hourly_avg = (
            plot_df.group_by(["month", "month_name", "hour", "height_display"])
            .agg(pl.col("wind_speed").mean().alias("wind_speed"))
            .sort(["month", "hour", "height_display"])
        )

        # Create line chart with points
        base = alt.Chart(hourly_avg).mark_line(strokeWidth=2).encode(
            x=alt.X(
                "hour:O",
                title="小时",
                axis=alt.Axis(
                    labelAngle=0,
                    tickCount=8,
                ),
            ),
            y=alt.Y(
                "wind_speed:Q",
                title="风速 (m/s)",
                scale=alt.Scale(zero=False),
            ),
            color=alt.Color(
                "height_display:N",
                title="高度",
                legend=alt.Legend(
                    orient="right",
                    titleFontSize=12,
                    labelFontSize=10,
                ),
            ),
            tooltip=[
                alt.Tooltip("month_name:N", title="月份"),
                alt.Tooltip("hour:Q", title="小时"),
                alt.Tooltip("height_display:N", title="高度"),
                alt.Tooltip("wind_speed:Q", title="风速", format=".2f"),
            ],
        )

        # Add points for better visibility
        points = alt.Chart(hourly_avg).mark_circle(size=40).encode(
            x=alt.X("hour:O", title=None),
            y=alt.Y("wind_speed:Q", title=None),
            color=alt.Color("height_display:N", title=None),
            tooltip=[
                alt.Tooltip("month_name:N", title="月份"),
                alt.Tooltip("hour:Q", title="小时"),
                alt.Tooltip("height_display:N", title="高度"),
                alt.Tooltip("wind_speed:Q", title="风速", format=".2f"),
            ],
        )

        # Combine line and points
        chart = (base + points).facet(
            facet=alt.Facet(
                "month_name:N",
                title=None,
                header=alt.Header(
                    labelFontSize=12,
                    labelAngle=0,
                ),
            ),
            columns=4,
        ).properties(
            title=alt.TitleParams(
                text=f"{self.meta.mast_name} 各月日变化风速曲线",
                fontSize=16,
                anchor="middle",
            ),
        ).configure_view(
            strokeWidth=0.5,
            stroke="#cccccc",
        ).configure_axis(
            labelFontSize=9,
            titleFontSize=10,
        )

        # Save with high resolution (1200x900px base, scale_factor=2 for 2400x1800)
        chart.save(image_path, format="png", scale_factor=2)

        return image_path

    @override
    def renderSummary(self) -> str:
        """Render Chinese narrative about daily wind patterns.

        Summarizes the diurnal wind speed variations and seasonal characteristics.
        """
        # Handle empty DataFrame case
        if self.df.is_empty():
            return (
                f"由图@fig-{self.get_or_compute_df_hashkey()} 可知，"
                f"测风塔{self.meta.mast_name}暂无有效的月日变化数据可供分析。"
            )

        # Calculate hourly averages across all months
        hourly_pattern = (
            self.df.group_by("hour")
            .agg(pl.col("mean_speed").mean().alias("avg_speed"))
            .sort("hour")
        )

        # Handle case where grouped data is empty or all null
        if hourly_pattern.is_empty() or hourly_pattern["avg_speed"].null_count() == len(hourly_pattern):
            return (
                f"由图@fig-{self.get_or_compute_df_hashkey()} 可知，"
                f"测风塔{self.meta.mast_name}暂无有效的月日变化数据可供分析。"
            )

        # Find peak and minimum hours
        max_row = hourly_pattern.filter(
            pl.col("avg_speed") == pl.col("avg_speed").max()
        ).row(0, named=True)
        min_row = hourly_pattern.filter(
            pl.col("avg_speed") == pl.col("avg_speed").min()
        ).row(0, named=True)

        peak_hour = max_row["hour"]
        min_hour = min_row["hour"]

        # Calculate monthly averages to identify windy/quiet months
        monthly_avg = (
            self.df.group_by("month")
            .agg(pl.col("mean_speed").mean().alias("avg_speed"))
            .sort("avg_speed", descending=True)
        )

        windiest_month = monthly_avg.row(0, named=True)["month"]
        calmest_month = monthly_avg.row(-1, named=True)["month"]

        windiest_name = _MONTH_NAMES.get(windiest_month, f"{windiest_month}月")
        calmest_name = _MONTH_NAMES.get(calmest_month, f"{calmest_month}月")

        return (
            f"由图@fig-{self.get_or_compute_df_hashkey()} 可知，"
            f"测风塔{self.meta.mast_name}在观测期间各月风速呈现明显的日变化特征。"
            f"一般而言，风速在{peak_hour}:00左右达到峰值，在{min_hour}:00左右达到谷值，"
            f"这种日变化规律与大气边界层的发展密切相关。"
            f"从季节分布来看，{windiest_name}风速较大，{calmest_name}风速相对较小，"
            f"反映了该地区风能资源的季节性变化特征。"
        )
