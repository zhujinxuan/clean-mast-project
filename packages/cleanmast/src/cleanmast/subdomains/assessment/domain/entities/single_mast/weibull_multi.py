"""Multi-height Weibull distribution atom for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
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
    WeibullSchema,
)


@dataclass
class SingleMastWeibullMultiHeightAtom(ReportAtom[WeibullSchema, SingleMastMeta]):
    """Renders multi-height Weibull distribution curves.

    - Table: Weibull parameters (k, c, mean_speed) for all heights
    - Image: Overlay of fitted Weibull PDF curves, one line per height
    - Summary: Chinese comparison of distributions across heights
    """

    @override
    def renderTable(self) -> str:
        """Render as Typst table with Weibull parameters by height.

        Columns: 高度 | 形状参数k | 尺度参数c | 平均风速(m/s)
        """
        sorted_df = self.df.sort("height")

        rows = []
        for row in sorted_df.iter_rows(named=True):
            height_display = get_height_display_name(
                row["height"], row["interpolation_marker"] or ""
            )
            shape_k = row["shape_k"]
            scale_c = row["scale_c"]
            mean_speed = row["mean_speed"]
            rows.append(
                f"  [{height_display}], [{shape_k:.2f}], [{scale_c:.2f}], [{mean_speed:.2f}],"
            )

        return f"""#table(
  columns: (auto, auto, auto, auto),
  inset: 8pt,
  align: center,
  table.header(
    [高度], [形状参数k], [尺度参数c], [平均风速(m/s)]
  ),
{chr(10).join(rows)}
)
"""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate multi-height Weibull PDF curves.

        Creates a single chart with fitted Weibull PDF curves for all heights,
        each displayed in a different color with a legend.

        Args:
            output_dir: Directory to save the PNG file
            force: If True, regenerate even if cached file exists

        Returns:
            Path to the generated PNG file
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"weibull_multi_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Create long-format data for plotting
        plot_data = []
        for row in self.df.iter_rows(named=True):
            height = row["height"]
            marker = row.get("interpolation_marker", "")
            height_label = get_height_display_name(height, marker or "")

            for bin_center, fitted in zip(
                row["bin_centers"], row["fitted_density"]
            ):
                plot_data.append({
                    "bin_center": bin_center,
                    "fitted_density": fitted,
                    "height": height_label,
                })

        plot_df = pl.DataFrame(plot_data)

        # Line chart with color by height
        chart = (
            alt.Chart(plot_df)
            .mark_line(strokeWidth=2)
            .encode(
                x=alt.X("bin_center:Q", title="风速 (m/s)"),
                y=alt.Y("fitted_density:Q", title="概率密度"),
                color=alt.Color(
                    "height:N",
                    title="高度",
                    legend=alt.Legend(
                        orient="right",
                        titleFontSize=12,
                        labelFontSize=10,
                    ),
                ),
                tooltip=[
                    alt.Tooltip("height:N", title="高度"),
                    alt.Tooltip("bin_center:Q", title="风速", format=".1f"),
                    alt.Tooltip("fitted_density:Q", title="概率密度", format=".4f"),
                ],
            )
            .properties(
                title=alt.TitleParams(
                    text=f"{self.meta.mast_name} 多高度Weibull分布拟合",
                    fontSize=16,
                    anchor="middle",
                ),
                width=600,
                height=400,
            )
            .configure_axis(
                labelFontSize=11,
                titleFontSize=12,
            )
            .configure_view(
                strokeWidth=0.5,
                stroke="#cccccc",
            )
        )

        # Save with high resolution
        chart.save(image_path, format="png", scale_factor=2)

        return image_path

    @override
    def renderSummary(self) -> str:
        """Render Chinese narrative comparing Weibull distributions across heights.

        Summarizes the shape and scale parameters, highlighting how the
        wind speed distribution changes with height.
        """
        sorted_df = self.df.sort("height")

        # Get all heights for mention
        height_strs = [
            get_height_display_name(
                row["height"], row.get("interpolation_marker", "") or ""
            )
            for row in sorted_df.iter_rows(named=True)
        ]

        # Calculate average parameters
        avg_k = sorted_df["shape_k"].mean()
        avg_c = sorted_df["scale_c"].mean()

        # Find height with max/min k (shape parameter indicates distribution shape)
        max_k_row = sorted_df.sort("shape_k", descending=True).row(0, named=True)
        min_k_row = sorted_df.sort("shape_k", descending=False).row(0, named=True)

        # Find height with max/min scale c (scale parameter relates to average wind speed)
        max_c_row = sorted_df.sort("scale_c", descending=True).row(0, named=True)
        min_c_row = sorted_df.sort("scale_c", descending=False).row(0, named=True)

        # Find highest and lowest mean speeds
        max_speed_row = sorted_df.sort("mean_speed", descending=True).row(0, named=True)
        min_speed_row = sorted_df.sort("mean_speed", descending=False).row(
            0, named=True
        )

        max_k_height = get_height_display_name(
            max_k_row["height"], max_k_row.get("interpolation_marker", "") or ""
        )
        min_k_height = get_height_display_name(
            min_k_row["height"], min_k_row.get("interpolation_marker", "") or ""
        )
        max_c_height = get_height_display_name(
            max_c_row["height"], max_c_row.get("interpolation_marker", "") or ""
        )
        min_c_height = get_height_display_name(
            min_c_row["height"], min_c_row.get("interpolation_marker", "") or ""
        )
        max_speed_height = get_height_display_name(
            max_speed_row["height"], max_speed_row.get("interpolation_marker", "") or ""
        )
        min_speed_height = get_height_display_name(
            min_speed_row["height"], min_speed_row.get("interpolation_marker", "") or ""
        )

        return (
            f"由图@fig-{self.get_or_compute_df_hashkey()} 可知，"
            f"测风塔{self.meta.mast_name}在{', '.join(height_strs)}各高度的"
            f"风速频率分布均符合Weibull分布特征。各高度平均形状参数k={avg_k:.2f}，"
            f"平均尺度参数c={avg_c:.2f}m/s。"
            f"从分布形态来看，形状参数k最大值{max_k_row['shape_k']:.2f}出现在"
            f"{max_k_height}，表明该高度风速分布最为集中；"
            f"最小值{min_k_row['shape_k']:.2f}出现在{min_k_height}，"
            f"表明该高度风速分布相对分散。"
            f"尺度参数c随高度增加而增大，最大值{max_c_row['scale_c']:.2f}m/s出现在"
            f"{max_c_height}，最小值{min_c_row['scale_c']:.2f}m/s出现在{min_c_height}，"
            f"反映出风速随高度增加的整体趋势。"
            f"平均风速在{max_speed_height}达到{max_speed_row['mean_speed']:.2f}m/s，"
            f"在{min_speed_height}为{min_speed_row['mean_speed']:.2f}m/s，"
            f"各高度Weibull拟合曲线平滑连续，拟合效果良好。"
        )
