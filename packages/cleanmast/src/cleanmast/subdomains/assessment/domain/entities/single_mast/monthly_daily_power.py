"""Monthly daily wind power pattern atom for 3x4 grid visualization.

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
class SingleMastMonthlyDailyPowerAtom(ReportAtom[TemporalPatternSchema, SingleMastMeta]):
    """Renders 3x4 grid of daily wind power patterns for each month.

    - Table: Summary table of monthly wind power statistics
    - Image: 3x4 grid of line charts (Jan-Dec), each showing 24-hour power pattern
    - Summary: Chinese description of daily wind power patterns
    """

    @override
    def renderTable(self) -> str:
        """Render summary table of monthly wind power statistics.

        Shows each month with its average wind power density and diurnal range.
        """
        # Calculate monthly statistics
        monthly_stats = (
            self.df.group_by("month")
            .agg([
                pl.col("mean_power").mean().alias("avg_power"),
                pl.col("mean_power").max().alias("max_power"),
                pl.col("mean_power").min().alias("min_power"),
                (pl.col("mean_power").max() - pl.col("mean_power").min()).alias("diurnal_range"),
            ])
            .sort("month")
        )

        rows = []
        for row in monthly_stats.iter_rows(named=True):
            month_name = _MONTH_NAMES.get(row["month"], f"{row['month']}月")
            rows.append(
                f'  [{month_name}], [{row["avg_power"]:.1f}], '
                f'[{row["max_power"]:.1f}], [{row["min_power"]:.1f}], '
                f'[{row["diurnal_range"]:.1f}],'
            )

        return f"""#table(
  columns: (auto, auto, auto, auto, auto),
  inset: 8pt,
  align: center,
  table.header(
    [月份], [平均功率密度(W/m²)], [最大功率密度(W/m²)], [最小功率密度(W/m²)], [日较差(W/m²)]
  ),
{chr(10).join(rows)}
)
"""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate 3x4 grid of monthly daily wind power patterns.

        Creates a faceted chart with 12 subplots (3 rows x 4 columns),
        one for each month. Each subplot shows the 24-hour wind power density pattern.

        Args:
            output_dir: Directory to save the PNG file
            force: If True, regenerate even if cached file exists

        Returns:
            Path to the generated PNG file
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"monthly_daily_power_{self.meta.mast_name}_{cache_key}.png"

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
            .agg(pl.col("mean_power").mean().alias("mean_power"))
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
                "mean_power:Q",
                title="风功率密度 (W/m²)",
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
                alt.Tooltip("mean_power:Q", title="风功率密度", format=".1f"),
            ],
        )

        # Add points for better visibility
        points = alt.Chart(hourly_avg).mark_circle(size=40).encode(
            x=alt.X("hour:O", title=None),
            y=alt.Y("mean_power:Q", title=None),
            color=alt.Color("height_display:N", title=None),
            tooltip=[
                alt.Tooltip("month_name:N", title="月份"),
                alt.Tooltip("hour:Q", title="小时"),
                alt.Tooltip("height_display:N", title="高度"),
                alt.Tooltip("mean_power:Q", title="风功率密度", format=".1f"),
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
                text=f"{self.meta.mast_name} 各月日变化风功率密度曲线",
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
        """Render Chinese narrative about daily wind power patterns.

        Summarizes the diurnal wind power density variations and seasonal characteristics.
        """
        # Calculate hourly averages across all months
        hourly_pattern = (
            self.df.group_by("hour")
            .agg(pl.col("mean_power").mean().alias("avg_power"))
            .sort("hour")
        )

        # Find peak and minimum hours
        max_row = hourly_pattern.filter(
            pl.col("avg_power") == pl.col("avg_power").max()
        ).row(0, named=True)
        min_row = hourly_pattern.filter(
            pl.col("avg_power") == pl.col("avg_power").min()
        ).row(0, named=True)

        peak_hour = max_row["hour"]
        min_hour = min_row["hour"]

        # Calculate monthly averages to identify high/low power months
        monthly_avg = (
            self.df.group_by("month")
            .agg(pl.col("mean_power").mean().alias("avg_power"))
            .sort("avg_power", descending=True)
        )

        highest_month = monthly_avg.row(0, named=True)["month"]
        lowest_month = monthly_avg.row(-1, named=True)["month"]

        highest_name = _MONTH_NAMES.get(highest_month, f"{highest_month}月")
        lowest_name = _MONTH_NAMES.get(lowest_month, f"{lowest_month}月")

        return (
            f"由图@fig-{self.get_or_compute_df_hashkey()} 可知，"
            f"测风塔{self.meta.mast_name}在观测期间各月风功率密度呈现明显的日变化特征。"
            f"一般而言，风功率密度在{peak_hour}:00左右达到峰值，在{min_hour}:00左右达到谷值，"
            f"这种日变化规律与风速的日变化及大气边界层的发展密切相关。"
            f"从季节分布来看，{highest_name}风功率密度较大，{lowest_name}风功率密度相对较小，"
            f"反映了该地区风能资源的季节性变化特征，对风电场功率预测和调度具有重要参考价值。"
        )
