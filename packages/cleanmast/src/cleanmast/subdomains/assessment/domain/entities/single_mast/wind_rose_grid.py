"""Wind rose grid atom for monthly 3x4 grid visualization.

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
    WindRoseSchema,
)


@dataclass
class SingleMastMonthlyWindRoseGridAtom(ReportAtom[WindRoseSchema, SingleMastMeta]):
    """Renders 3x4 grid of monthly wind roses for all 12 months.

    - Table: Summary table of monthly dominant directions
    - Image: 3x4 grid of polar charts (Jan-Dec)
    - Summary: Chinese description of seasonal patterns
    """

    @override
    def renderTable(self) -> str:
        """Render summary table of monthly dominant directions.

        Shows each month with its dominant sector and frequency.
        """
        # Find dominant sector for each month
        monthly_dominant = (
            self.df.group_by(["month", "month_name"])
            .agg([
                pl.col("sector_name").get(pl.col("frequency").arg_max()).alias("dominant_sector"),
                pl.col("frequency").max().alias("max_frequency"),
            ])
            .sort("month")
        )

        rows = []
        for row in monthly_dominant.iter_rows(named=True):
            freq_pct = row["max_frequency"] * 100
            rows.append(f'  [{row["month_name"]}], [{row["dominant_sector"]}], [{freq_pct:.1f}%],')

        return f"""#table(
  columns: (auto, auto, auto),
  inset: 8pt,
  align: center,
  table.header(
    [月份], [主导风向], [频率]
  ),
{chr(10).join(rows)}
)
"""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate 3x4 grid of monthly wind roses.

        Creates a faceted chart with 12 subplots (3 rows x 4 columns),
        one for each month. Shows wind frequency by direction.

        Args:
            output_dir: Directory to save the PNG file
            force: If True, regenerate even if cached file exists

        Returns:
            Path to the generated PNG file
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"windroserose_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Filter to >=100m heights for visualization
        plot_df = self.df.filter(pl.col("height") >= 100)

        # Add display name for legend
        plot_df = plot_df.with_columns(
            pl.struct(["height", "interpolation_marker"])
            .map_elements(
                lambda x: get_height_display_name(x["height"], x["interpolation_marker"])
            )
            .alias("height_display")
        )

        # Create base chart with polar coordinates
        base = alt.Chart(plot_df).mark_arc(stroke="white", strokeWidth=1).encode(
            theta=alt.Theta("sector:O", sort=None, title=None),
            radius=alt.Radius(
                "frequency:Q",
                scale=alt.Scale(zero=True),
                title=None,
            ),
            radius2=alt.datum(0),
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
                alt.Tooltip("sector_name:N", title="风向"),
                alt.Tooltip("height_display:N", title="高度"),
                alt.Tooltip("frequency:Q", title="频率", format=".1%"),
            ],
        )

        # Facet by month (3 rows x 4 columns)
        chart = base.facet(
            facet=alt.Facet(
                "month_name:N",
                title=None,
                header=alt.Header(
                    labelFontSize=11,
                    labelAngle=0,
                ),
            ),
            columns=4,
        ).properties(
            title=alt.TitleParams(
                text=f"{self.meta.mast_name} 各月风向频率玫瑰图",
                fontSize=16,
                anchor="middle",
            ),
        ).configure_view(
            strokeWidth=0.5,
            stroke="#cccccc",
        )

        # Save with high resolution
        chart.save(image_path, format="png", scale_factor=2)

        return image_path

    @override
    def renderSummary(self) -> str:
        """Render Chinese narrative about seasonal wind patterns.

        Summarizes the dominant wind directions and seasonal variations.
        """
        # Find dominant sector for each month
        monthly_dominant = (
            self.df.group_by(["month", "month_name"])
            .agg([
                pl.col("sector_name").get(pl.col("frequency").arg_max()).alias("dominant_sector"),
                pl.col("frequency").max().alias("max_frequency"),
            ])
            .sort("month")
        )

        # Get overall dominant sectors across all months
        sector_counts = (
            monthly_dominant.group_by("dominant_sector")
            .len()
            .sort("len", descending=True)
        )

        dominant_sectors = sector_counts["dominant_sector"].to_list()[:3]
        sectors_str = "、".join(dominant_sectors)

        return (
            f"由图@fig-{self.get_or_compute_df_hashkey()} 可知，"
            f"测风塔{self.meta.mast_name}在观测期间各月主导风向以{sectors_str}为主，"
            f"反映了该测风塔的风能资源方向特征。"
            f"各月风向频率玫瑰图显示，风向分布存在季节性变化特征。"
        )
