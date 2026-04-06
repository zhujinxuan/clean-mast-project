"""Vertical profile atom for single mast analysis.

ADR-GUARDRAILS: ddd-t-003-report-atoms, structure-001-subdomain-layout
Compliance: ReportAtom ✓ | Content-Addressable ✓ | Altair Rendering ✓
"""

from dataclasses import dataclass
from pathlib import Path

import altair as alt
import numpy as np
import polars as pl
import vl_convert as vlc
from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.value_objects.schemas import (
    VerticalProfileSchema,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
    get_height_display_name,
)


@dataclass
class SingleMastVerticalProfileAtom(ReportAtom[VerticalProfileSchema, SingleMastMeta]):
    """Renders vertical wind profile with power law fit on log-log chart.

    - Table: Height, wind speed, alpha, R² per height level
    - Image: Log-log scatter + line chart showing measured data and power law fit
    - Summary: Chinese description with terrain classification based on alpha
    """

    @override
    def renderTable(self) -> str:
        """Render as Typst table with vertical profile data per height.

        Columns: 高度 | 平均风速(m/s) | 风切变指数α | 拟合优度R²
        """
        # Sort by height for consistent ordering
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")

        # Build table rows - one row per height
        rows = []
        for row in heights_df.iter_rows(named=True):
            height = row["height"]
            marker = row["interpolation_marker"]
            display = get_height_display_name(height, marker or "")

            # Get data for this height
            height_data = self.df.filter(pl.col("height") == height).row(0, named=True)
            wind_speed_mean = height_data["wind_speed_mean"]
            alpha = height_data["alpha"]
            r_squared = height_data["r_squared"]

            # Format alpha and r_squared (same for all heights, may be None)
            alpha_str = f"{alpha:.3f}" if alpha is not None else "-"
            r_squared_str = f"{r_squared:.3f}" if r_squared is not None else "-"

            rows.append(f"  [{display}], [{wind_speed_mean:.2f}], [{alpha_str}], [{r_squared_str}],")

        return f"""#table(
  columns: (auto, auto, auto, auto),
  inset: 8pt,
  align: center,
  table.header(
    [高度], [平均风速(m/s)], [风切变指数α], [拟合优度R²]
  ),
{chr(10).join(rows)}
)
"""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate log-log vertical profile chart with scatter and power law fit.

        Chart shows:
        - Scatter points: measured wind speeds vs heights (log-log)
        - Line: power law fit curve

        Uses Altair with log scales, exports via vl-convert.
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"vertical_profile_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Get profile data sorted by height
        profile_df = self.df.sort("height")

        # Extract alpha and r_squared (same for all rows)
        first_row = profile_df.row(0, named=True)
        alpha = first_row.get("alpha")
        r_squared = first_row.get("r_squared")

        # Prepare data for plotting - measured points
        plot_data = []
        for row in profile_df.iter_rows(named=True):
            plot_data.append({
                "height": row["height"],
                "wind_speed": row["wind_speed_mean"],
                "type": "实测数据",
                "display_name": get_height_display_name(row["height"], row["interpolation_marker"] or ""),
            })

        # Create power law fit line data if alpha is available
        if alpha is not None and len(plot_data) >= 2:
            # Get height range for fit line
            heights = [r["height"] for r in plot_data]
            min_h, max_h = min(heights), max(heights)

            # Generate fit line points (more points for smooth curve)
            fit_heights = np.logspace(np.log10(min_h), np.log10(max_h), 50)

            # Power law: v = v_ref * (h/h_ref)^alpha
            # Use first measured point as reference
            ref_h = plot_data[0]["height"]
            ref_v = plot_data[0]["wind_speed"]

            for h in fit_heights:
                v = ref_v * (h / ref_h) ** alpha
                plot_data.append({
                    "height": h,
                    "wind_speed": v,
                    "type": "幂律拟合",
                    "display_name": "拟合曲线",
                })

        # Convert to DataFrame
        plot_df = pl.DataFrame(plot_data).to_pandas()

        # Create scatter plot for measured data
        scatter = alt.Chart(plot_df[plot_df["type"] == "实测数据"]).mark_point(
            size=100,
            filled=True,
        ).encode(
            x=alt.X(
                "height:Q",
                scale=alt.Scale(type="log"),
                title="高度(m)",
            ),
            y=alt.Y(
                "wind_speed:Q",
                scale=alt.Scale(type="log"),
                title="风速(m/s)",
            ),
            color=alt.value("#1f77b4"),
            tooltip=[
                alt.Tooltip("display_name:N", title="高度"),
                alt.Tooltip("height:Q", title="高度(m)", format=".1f"),
                alt.Tooltip("wind_speed:Q", title="风速(m/s)", format=".2f"),
            ],
        )

        # Create line for power law fit
        if alpha is not None:
            fit_line = alt.Chart(plot_df[plot_df["type"] == "幂律拟合"]).mark_line(
                strokeWidth=2,
            ).encode(
                x=alt.X("height:Q", scale=alt.Scale(type="log")),
                y=alt.Y("wind_speed:Q", scale=alt.Scale(type="log")),
                color=alt.value("#ff7f0e"),
                tooltip=[
                    alt.Tooltip("height:Q", title="高度(m)", format=".1f"),
                    alt.Tooltip("wind_speed:Q", title="拟合风速(m/s)", format=".2f"),
                ],
            )
            chart = scatter + fit_line
        else:
            chart = scatter

        # Format title with alpha and R²
        alpha_str = f"{alpha:.3f}" if alpha is not None else "N/A"
        r_squared_str = f"{r_squared:.3f}" if r_squared is not None else "N/A"
        title = f"{self.meta.mast_name} 垂直风廓线 (α={alpha_str}, R²={r_squared_str})"

        final_chart = chart.properties(
            title=title,
            width=500,
            height=400,
        )

        # Export to PNG
        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(final_chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> str:
        """Generate Chinese summary with terrain classification based on alpha."""
        # Handle empty data
        if self.df.height == 0:
            return f"{self.meta.mast_name}测风塔无垂直风廓线数据。"

        # Get unique heights
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_strs = [
            get_height_display_name(row["height"], row["interpolation_marker"] or "")
            for row in heights_df.iter_rows(named=True)
        ]

        # Get alpha and r_squared from first row (same for all)
        first_row = self.df.row(0, named=True)
        alpha = first_row.get("alpha")
        r_squared = first_row.get("r_squared")

        # Calculate mean wind speed across all heights
        mean_speed = self.df["wind_speed_mean"].mean()

        # Terrain classification based on alpha
        terrain_desc = self._classify_terrain(alpha)

        # Fit quality assessment
        if r_squared is not None:
            if r_squared >= 0.95:
                fit_quality = "拟合效果优秀"
            elif r_squared >= 0.85:
                fit_quality = "拟合效果良好"
            elif r_squared >= 0.70:
                fit_quality = "拟合效果一般"
            else:
                fit_quality = "拟合效果有待改进"
            fit_desc = f"{fit_quality}(R²={r_squared:.3f})"
        else:
            fit_desc = "无法进行幂律拟合"

        # Alpha description
        if alpha is not None:
            alpha_desc = f"风切变指数α={alpha:.3f}"
        else:
            alpha_desc = "风切变指数无法计算"

        return (
            f"{self.meta.mast_name}测风塔垂直风廓线分析。"
            f"分析高度包括{', '.join(height_strs)}。"
            f"各高度平均风速{mean_speed:.2f}m/s，"
            f"{alpha_desc}，"
            f"{terrain_desc}。"
            f"幂律拟合{fit_desc}。"
            f"该分析结果可用于风机轮毂高度风速推算和风资源评估。"
        )

    def _classify_terrain(self, alpha: float | None) -> str:
        """Classify terrain roughness based on alpha value.

        Args:
            alpha: Wind shear exponent

        Returns:
            Chinese terrain classification description
        """
        if alpha is None:
            return "地形类型无法确定"

        if alpha < 0.12:
            return "地形类型为平滑（水面），风切变较小"
        elif alpha < 0.16:
            return "地形类型为开阔（草地），风切变适中"
        elif alpha < 0.25:
            return "地形类型为粗糙（郊区），风切变较大"
        else:
            return "地形类型为非常粗糙（城市），风切变很大"
