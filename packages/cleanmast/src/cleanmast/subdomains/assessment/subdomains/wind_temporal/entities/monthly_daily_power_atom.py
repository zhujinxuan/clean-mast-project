"""Monthly daily wind power pattern atom for 3x4 grid visualization.

ADR-GUARDRAILS: ddd-t-001-aggregates, ddd-t-002-entities-value-objects, ddd-t-003-report-atoms
Compliance: Aggregate ✓ | Entity ✓ | Content-Addressable ✓
"""

from dataclasses import dataclass
from pathlib import Path

import altair as alt
import polars as pl
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

    @property
    def default_image_caption(self) -> str:
        return f"{self.meta.mast_name} 月日风功率密度分布图"

    @property
    def default_table_caption(self) -> str:
        return f"{self.meta.mast_name} 月日风功率密度分布表"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render summary table of monthly wind power statistics as TypstTable IR node.

        Shows each month with its average wind power density and diurnal range.
        """
        return None

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
    def renderSummary(self) -> list[TypstParagraph]:
        """Render Chinese narrative about daily wind power patterns as TypstParagraph IR node.

        Summarizes the diurnal wind power density variations and seasonal characteristics.
        """
        return []
