"""Turbulence intensity atom for single mast analysis.

ADR-GUARDRAILS: ddd-t-003-report-atoms, structure-001-subdomain-layout
Compliance: ReportAtom ✓ | Content-Addressable ✓ | Altair Rendering ✓
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
    TurbulenceSchema,
)

# IEC reference turbulence intensity parameters
IEC_CATEGORIES = {
    "A+": 0.18,
    "A": 0.16,
    "B": 0.14,
    "C": 0.12,
}


def compute_iec_ti(i_ref: float, wind_speed: float) -> float:
    """Compute IEC reference turbulence intensity.

    Formula: TI_IEC = I_ref * (0.75 + 5.6/V)

    Args:
        i_ref: Reference turbulence intensity (varies by category)
        wind_speed: Wind speed in m/s

    Returns:
        IEC reference TI value
    """
    if wind_speed < 0.5:
        return i_ref * (0.75 + 5.6 / 0.5)
    return i_ref * (0.75 + 5.6 / wind_speed)


@dataclass
class SingleMastTurbulenceIntensityAtom(ReportAtom[TurbulenceSchema, SingleMastMeta]):
    """Renders turbulence intensity vs wind speed with IEC band fills.

    - Table: Wind speed bin, height, mean TI, representative TI, IEC category per height
    - Image: Line chart with representative TI vs wind speed, IEC bands as area fills
    - Summary: Chinese description of IEC classification statistics
    """

    @override
    def renderTable(self) -> str:
        """Render as Typst table with turbulence intensity data.

        Columns: 风速(m/s) | 高度 | 平均TI | 代表TI | IEC类别
        """
        # Sort by wind speed bin and height for consistent display
        sorted_df = self.df.sort(["wind_speed_bin", "height"])

        # Build table rows
        rows = []
        for row in sorted_df.iter_rows(named=True):
            wind_speed = row["wind_speed_bin"]
            height_display = get_height_display_name(row["height"], row["interpolation_marker"] or "")
            mean_ti = row["mean_ti"]
            rep_ti = row["representative_ti"]
            iec_cat = row["iec_category"]
            rows.append(
                f"  [{wind_speed}], [{height_display}], [{mean_ti:.3f}], [{rep_ti:.3f}], [{iec_cat}],"
            )

        return f"""#table(
  columns: (auto, auto, auto, auto, auto),
  inset: 8pt,
  align: center,
  table.header(
    [风速(m/s)], [高度], [平均TI], [代表TI], [IEC类别]
  ),
{chr(10).join(rows)}
)
"""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate turbulence intensity charts - one per height with IEC bands.

        Each chart shows:
        - Representative TI line vs wind speed
        - IEC category reference bands (A+, A, B, C) as area fills

        Uses Altair with line for TI, area for IEC bands, exports via vl-convert.
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"turbulence_intensity_{self.meta.mast_name}_{cache_key}.png"

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
            height_data = self.df.filter(pl.col("height") == height).sort("wind_speed_bin")

            # Create DataFrame for plotting
            plot_df = height_data.select([
                "wind_speed_bin",
                "mean_ti",
                "representative_ti",
                "iec_category",
            ]).to_pandas()

            # Generate IEC reference curves for this wind speed range
            wind_speeds = plot_df["wind_speed_bin"].tolist()
            iec_data = []
            for v in wind_speeds:
                iec_data.append({
                    "wind_speed": v,
                    "ti_a_plus": compute_iec_ti(IEC_CATEGORIES["A+"], v),
                    "ti_a": compute_iec_ti(IEC_CATEGORIES["A"], v),
                    "ti_b": compute_iec_ti(IEC_CATEGORIES["B"], v),
                    "ti_c": compute_iec_ti(IEC_CATEGORIES["C"], v),
                })
            iec_df = pl.DataFrame(iec_data).to_pandas()

            # IEC A+ band (highest TI) - fill from A+ down to A
            band_a_plus = alt.Chart(iec_df).mark_area(opacity=0.15, color="#d62728").encode(
                x=alt.X("wind_speed:Q", title="风速 (m/s)"),
                y=alt.Y("ti_a:Q", title="湍流强度"),
                y2=alt.Y2("ti_a_plus:Q"),
            )

            # IEC A band - fill from A down to B
            band_a = alt.Chart(iec_df).mark_area(opacity=0.15, color="#ff7f0e").encode(
                x=alt.X("wind_speed:Q"),
                y=alt.Y("ti_b:Q"),
                y2=alt.Y2("ti_a:Q"),
            )

            # IEC B band - fill from B down to C
            band_b = alt.Chart(iec_df).mark_area(opacity=0.15, color="#2ca02c").encode(
                x=alt.X("wind_speed:Q"),
                y=alt.Y("ti_c:Q"),
                y2=alt.Y2("ti_b:Q"),
            )

            # IEC reference lines
            line_a_plus = alt.Chart(iec_df).mark_line(strokeDash=[4, 4], color="#d62728").encode(
                x=alt.X("wind_speed:Q"),
                y=alt.Y("ti_a_plus:Q"),
            )

            line_a = alt.Chart(iec_df).mark_line(strokeDash=[4, 4], color="#ff7f0e").encode(
                x=alt.X("wind_speed:Q"),
                y=alt.Y("ti_a:Q"),
            )

            line_b = alt.Chart(iec_df).mark_line(strokeDash=[4, 4], color="#2ca02c").encode(
                x=alt.X("wind_speed:Q"),
                y=alt.Y("ti_b:Q"),
            )

            line_c = alt.Chart(iec_df).mark_line(strokeDash=[4, 4], color="#1f77b4").encode(
                x=alt.X("wind_speed:Q"),
                y=alt.Y("ti_c:Q"),
            )

            # Representative TI line
            ti_line = alt.Chart(plot_df).mark_line(strokeWidth=2.5, color="#333333").encode(
                x=alt.X("wind_speed_bin:Q", title="风速 (m/s)"),
                y=alt.Y("representative_ti:Q", title="湍流强度", scale=alt.Scale(zero=False)),
                tooltip=[
                    alt.Tooltip("wind_speed_bin:Q", title="风速(m/s)"),
                    alt.Tooltip("representative_ti:Q", title="代表TI", format=".3f"),
                    alt.Tooltip("iec_category:N", title="IEC类别"),
                ],
            )

            # Mean TI points for reference
            ti_points = alt.Chart(plot_df).mark_point(filled=True, size=60, color="#333333").encode(
                x=alt.X("wind_speed_bin:Q"),
                y=alt.Y("mean_ti:Q"),
                tooltip=[
                    alt.Tooltip("wind_speed_bin:Q", title="风速(m/s)"),
                    alt.Tooltip("mean_ti:Q", title="平均TI", format=".3f"),
                ],
            )

            # Combine all layers
            chart = (
                band_a_plus
                + band_a
                + band_b
                + line_a_plus
                + line_a
                + line_b
                + line_c
                + ti_line
                + ti_points
            ).properties(
                title=f"{display} 湍流强度分布",
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
                title=f"{self.meta.mast_name} 湍流强度与IEC参考曲线"
            )

        # Export to PNG
        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(final_chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> str:
        """Generate Chinese summary of IEC classification statistics."""
        # Get unique heights
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_strs = [
            get_height_display_name(row["height"], row["interpolation_marker"] or "")
            for row in heights_df.iter_rows(named=True)
        ]

        # Count IEC categories per height
        category_counts = []
        for row in heights_df.iter_rows(named=True):
            height = row["height"]
            marker = row["interpolation_marker"] or ""
            height_data = self.df.filter(pl.col("height") == height)

            # Count categories
            cats = height_data["iec_category"].value_counts()
            total = len(height_data)

            cat_stats = {}
            for cat_row in cats.iter_rows(named=True):
                cat = cat_row["iec_category"]
                count = cat_row["count"]
                cat_stats[cat] = count / total * 100

            # Get representative TI range
            rep_ti_min = height_data["representative_ti"].min()
            rep_ti_max = height_data["representative_ti"].max()
            rep_ti_mean = height_data["representative_ti"].mean()

            category_counts.append({
                "height": height,
                "marker": marker,
                "display": get_height_display_name(height, marker),
                "cat_stats": cat_stats,
                "rep_ti_min": rep_ti_min,
                "rep_ti_max": rep_ti_max,
                "rep_ti_mean": rep_ti_mean,
                "total": total,
            })

        # Find dominant category overall
        all_cats = self.df["iec_category"].value_counts()
        dominant_cat = all_cats.row(0, named=True)["iec_category"]
        dominant_pct = all_cats.row(0, named=True)["count"] / len(self.df) * 100

        # Average representative TI
        avg_rep_ti = self.df["representative_ti"].mean()

        # Build height-specific descriptions
        height_descriptions = []
        for stats in category_counts:
            desc = f"{stats['display']}: 代表TI范围{stats['rep_ti_min']:.3f}~{stats['rep_ti_max']:.3f}"
            if stats["cat_stats"]:
                cat_desc = ", ".join([f"{cat}类占{pct:.0f}%" for cat, pct in stats["cat_stats"].items()])
                desc += f" ({cat_desc})"
            height_descriptions.append(desc)

        # IEC category descriptions
        cat_meanings = {
            "A+": "高湍流",
            "A": "较高湍流",
            "B": "中等湍流",
            "C": "低湍流",
        }
        dominant_meaning = cat_meanings.get(dominant_cat, "未知")

        return (
            f"{self.meta.mast_name}测风塔湍流强度分析。"
            f"分析高度包括{', '.join(height_strs)}。"
            f"整体主导IEC类别为{dominant_cat}类({dominant_meaning})，占比{dominant_pct:.0f}%。"
            f"平均代表湍流强度为{avg_rep_ti:.3f}。"
            f"各高度详细情况：{'；'.join(height_descriptions)}。"
            f"湍流强度数据可用于风电机组选型和控制策略制定。"
        )
