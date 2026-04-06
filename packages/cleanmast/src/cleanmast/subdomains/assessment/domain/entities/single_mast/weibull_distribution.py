"""Weibull distribution atom for single mast analysis.

ADR-GUARDRAILS: ddd-t-003-report-atoms, structure-001-subdomain-layout
Compliance: ReportAtom ✓ | Content-Addressable ✓ | Altair Rendering ✓
"""

from dataclasses import dataclass
from pathlib import Path
from typing import cast

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
    WeibullSchema,
)


@dataclass
class SingleMastWeibullDistributionAtom(ReportAtom[WeibullSchema, SingleMastMeta]):
    """Renders Weibull distribution fit (observed histogram + fitted PDF) per height.

    - Table: Weibull parameters (shape k, scale c, mean speed) per height
    - Image: One chart per height showing observed histogram bars and fitted PDF line
    - Summary: Chinese description of fit quality and distribution characteristics
    """

    @override
    def renderTable(self) -> str:
        """Render as Typst table with Weibull parameters per height.

        Columns: 高度 | 形状参数k | 尺度参数c(m/s) | 平均风速(m/s)
        """
        # Get unique heights and their display names
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")

        # Build table rows - one row per height
        rows = []
        for row in heights_df.iter_rows(named=True):
            height = row["height"]
            marker = row["interpolation_marker"]
            display = get_height_display_name(height, marker)

            # Get Weibull parameters for this height
            height_data = self.df.filter(pl.col("height") == height).row(0, named=True)
            shape_k = height_data["shape_k"]
            scale_c = height_data["scale_c"]
            mean_speed = height_data["mean_speed"]

            rows.append(f"  [{display}], [{shape_k:.3f}], [{scale_c:.3f}], [{mean_speed:.2f}],")

        return f"""#table(
  columns: (auto, auto, auto, auto),
  inset: 8pt,
  align: center,
  table.header(
    [高度], [形状参数k], [尺度参数c(m/s)], [平均风速(m/s)]
  ),
{chr(10).join(rows)}
)
"""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate Weibull distribution charts - one per height.

        Each chart shows:
        - Observed wind speed histogram (bar marks)
        - Fitted Weibull PDF curve (line mark)

        Uses Altair with bar for histogram, line for PDF, exports via vl-convert.
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"weibull_dist_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Build charts for each height
        charts = []
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")

        for row in heights_df.iter_rows(named=True):
            height = row["height"]
            marker = row["interpolation_marker"]
            display = get_height_display_name(height, marker)

            # Get data for this height
            height_row = self.df.filter(pl.col("height") == height).row(0, named=True)
            bin_centers = height_row["bin_centers"]
            observed_density = height_row["observed_density"]
            fitted_density = height_row["fitted_density"]
            shape_k = height_row["shape_k"]
            scale_c = height_row["scale_c"]

            # Create DataFrame for plotting
            plot_df = pl.DataFrame({
                "bin_centers": bin_centers,
                "observed_density": observed_density,
                "fitted_density": fitted_density,
            }).to_pandas()

            # Observed histogram (bar marks)
            observed = alt.Chart(plot_df).mark_bar(opacity=0.6).encode(
                x=alt.X("bin_centers:Q", title="风速 (m/s)"),
                y=alt.Y("observed_density:Q", title="概率密度"),
                color=alt.value("#1f77b4"),
                tooltip=[
                    alt.Tooltip("bin_centers:Q", title="风速(m/s)", format=".1f"),
                    alt.Tooltip("observed_density:Q", title="观测密度", format=".4f"),
                ],
            )

            # Fitted Weibull PDF (line mark)
            fitted = alt.Chart(plot_df).mark_line(strokeWidth=2).encode(
                x=alt.X("bin_centers:Q"),
                y=alt.Y("fitted_density:Q"),
                color=alt.value("#ff7f0e"),
                tooltip=[
                    alt.Tooltip("bin_centers:Q", title="风速(m/s)", format=".1f"),
                    alt.Tooltip("fitted_density:Q", title="拟合密度", format=".4f"),
                ],
            )

            # Combined chart for this height
            chart = (observed + fitted).properties(
                title=f"{display} Weibull分布 (k={shape_k:.2f}, c={scale_c:.2f})",
                width=400,
                height=300,
            )
            charts.append(chart)

        # Arrange charts in a grid (2 columns if multiple heights)
        if len(charts) == 1:
            final_chart = charts[0]
        else:
            # Arrange in rows of 2
            rows = []
            for i in range(0, len(charts), 2):
                if i + 1 < len(charts):
                    rows.append(alt.hconcat(charts[i], charts[i + 1]))
                else:
                    rows.append(charts[i])
            final_chart = alt.vconcat(*rows).properties(
                title=f"{self.meta.mast_name} Weibull分布拟合"
            )

        # Export to PNG
        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(final_chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> str:
        """Generate Chinese summary of Weibull fit quality and distribution characteristics."""
        # Get unique heights
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_strs = [
            get_height_display_name(row["height"], row["interpolation_marker"])
            for row in heights_df.iter_rows(named=True)
        ]

        # Calculate fit quality metrics (RMSE between observed and fitted)
        fit_qualities = []
        for row in self.df.iter_rows(named=True):
            observed = pl.Series(row["observed_density"])
            fitted = pl.Series(row["fitted_density"])
            # Simple RMSE
            rmse = cast(float, ((observed - fitted) ** 2).mean() or 0) ** 0.5
            fit_qualities.append({
                "height": row["height"],
                "marker": row["interpolation_marker"],
                "shape_k": row["shape_k"],
                "scale_c": row["scale_c"],
                "mean_speed": row["mean_speed"],
                "rmse": rmse,
            })

        # Find best and worst fits
        fit_df = pl.DataFrame(fit_qualities)
        best_fit = fit_df.sort("rmse").row(0, named=True)
        worst_fit = fit_df.sort("rmse", descending=True).row(0, named=True)

        best_display = get_height_display_name(best_fit["height"], best_fit["marker"])
        worst_display = get_height_display_name(worst_fit["height"], worst_fit["marker"])

        # Calculate average shape parameter
        avg_k = cast(float, fit_df["shape_k"].mean() or 0)
        avg_c = cast(float, fit_df["scale_c"].mean() or 0)

        # Determine distribution type based on shape parameter k
        if avg_k < 1.5:
            dist_type = "低风速偏态分布，风速较低区间频率较高"
        elif avg_k < 2.0:
            dist_type = "中等偏态分布，接近瑞利分布"
        elif avg_k < 2.5:
            dist_type = "接近正态分布，风速分布较为均匀"
        else:
            dist_type = "高k值分布，风速集中在中高风速区间"

        # Overall fit quality assessment
        avg_rmse = cast(float, fit_df["rmse"].mean() or 0)
        if avg_rmse < 0.005:
            quality_desc = "拟合效果优秀"
        elif avg_rmse < 0.01:
            quality_desc = "拟合效果良好"
        elif avg_rmse < 0.02:
            quality_desc = "拟合效果一般"
        else:
            quality_desc = "拟合效果有待改进"

        return (
            f"{self.meta.mast_name}测风塔Weibull分布拟合分析。"
            f"分析高度包括{', '.join(height_strs)}。"
            f"平均形状参数k={avg_k:.3f}，平均尺度参数c={avg_c:.3f}m/s，"
            f"{dist_type}。"
            f"{quality_desc}，平均拟合误差RMSE={avg_rmse:.4f}，"
            f"其中{best_display}拟合最佳(RMSE={best_fit['rmse']:.4f})，"
            f"{worst_display}拟合相对较差(RMSE={worst_fit['rmse']:.4f})。"
            f"该分布模型可用于风能资源评估和发电量估算。"
        )
