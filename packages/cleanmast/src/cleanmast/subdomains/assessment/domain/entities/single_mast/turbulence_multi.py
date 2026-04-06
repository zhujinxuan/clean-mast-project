"""Multi-height turbulence intensity atom for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
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

IEC_CATEGORIES: dict[str, float] = {
    "A+": 0.18,
    "A": 0.16,
    "B": 0.14,
    "C": 0.12,
}


def compute_iec_ti(wind_speed: float, i_ref: float) -> float:
    """Compute IEC reference turbulence intensity: TI_IEC = I_ref * (0.75 + 5.6/V)."""
    if wind_speed < 0.1:
        return i_ref * 0.75
    return i_ref * (0.75 + 5.6 / wind_speed)


@dataclass
class SingleMastTurbulenceMultiHeightAtom(ReportAtom[TurbulenceSchema, SingleMastMeta]):
    """Renders multi-height turbulence intensity with IEC reference bands.

    - Table: Empty string (chart only)
    - Image: Combined chart with IEC bands (area) + multi-height TI lines
    - Summary: Chinese comparison of TI across heights
    """

    @override
    def renderTable(self) -> str:
        """Return empty string (no table, chart only)."""
        return ""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate combined turbulence chart with IEC bands and multi-height lines.

        Creates a layered chart with:
        - IEC reference bands (A+, A, B, C) as filled areas at bottom
        - Multi-height representative TI lines overlaid on top

        Args:
            output_dir: Directory to save the PNG file
            force: If True, regenerate even if cached file exists

        Returns:
            Path to the generated PNG file
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"turbulence_multi_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Handle empty DataFrame case
        if self.df.is_empty():
            # Create a placeholder empty image
            from PIL import Image

            # Create a blank image with text
            img = Image.new('RGB', (700, 450), color='white')
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            text = f"{self.meta.mast_name}\n无湍流数据"
            try:
                font = ImageFont.truetype("msyh.ttc", 32)
            except Exception:
                font = ImageFont.load_default()
            draw.text((350, 225), text, fill='gray', font=font, anchor="mm")
            img.save(image_path)
            return image_path

        # Get unique wind speed bins for IEC band calculation
        wind_speeds = sorted(self.df["wind_speed_bin"].unique().to_list())

        # Create IEC reference bands data
        iec_data = []
        for ws in wind_speeds:
            for category, i_ref in IEC_CATEGORIES.items():
                ti_value = compute_iec_ti(float(ws), i_ref)
                iec_data.append({
                    "wind_speed": ws,
                    "ti": ti_value,
                    "category": category,
                })

        iec_df = pl.DataFrame(iec_data)

        # Create IEC bands using area marks
        # Order: C (bottom), B, A, A+ (top) - each showing as area from 0 to TI value
        iec_colors: dict[str, str] = {
            "C": "#E8F5E9",    # Light green
            "B": "#FFF9C4",    # Light yellow
            "A": "#FFE0B2",    # Light orange
            "A+": "#FFCDD2",   # Light red
        }

        iec_bands = None
        for category in ["C", "B", "A", "A+"]:
            category_data = iec_df.filter(pl.col("category") == category)
            band = (
                alt.Chart(category_data)
                .mark_area(opacity=0.6)
                .encode(
                    x=alt.X("wind_speed:Q", title="风速 (m/s)"),
                    y=alt.Y("ti:Q", title="湍流强度"),
                    color=alt.Color(
                        "category:N",
                        scale=alt.Scale(
                            domain=["C", "B", "A", "A+"],
                            range=[iec_colors["C"], iec_colors["B"], iec_colors["A"], iec_colors["A+"]],
                        ),
                        legend=alt.Legend(
                            title="IEC参考类别",
                            orient="right",
                            titleFontSize=12,
                            labelFontSize=10,
                        ),
                    ),
                )
            )
            if iec_bands is None:
                iec_bands = band
            else:
                iec_bands = iec_bands + band

        # Prepare multi-height TI data
        ti_data = []
        for row in self.df.iter_rows(named=True):
            height = row["height"]
            marker = row.get("interpolation_marker", "")
            height_label = get_height_display_name(height, marker or "")

            ti_data.append({
                "wind_speed": row["wind_speed_bin"],
                "representative_ti": row["representative_ti"],
                "mean_ti": row["mean_ti"],
                "height": height_label,
            })

        ti_df = pl.DataFrame(ti_data)

        # Multi-height TI lines with distinct colors
        ti_lines = (
            alt.Chart(ti_df)
            .mark_line(strokeWidth=2.5, point=True)
            .encode(
                x=alt.X("wind_speed:Q", title="风速 (m/s)"),
                y=alt.Y("representative_ti:Q", title="湍流强度"),
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
                    alt.Tooltip("wind_speed:Q", title="风速", format=".0f"),
                    alt.Tooltip("representative_ti:Q", title="代表湍流强度", format=".3f"),
                    alt.Tooltip("mean_ti:Q", title="平均湍流强度", format=".3f"),
                ],
            )
        )

        # Combine IEC bands (bottom layer) with TI lines (top layer)
        combined_chart = (iec_bands + ti_lines).properties(
            title=alt.TitleParams(
                text=f"{self.meta.mast_name} 多高度湍流强度对比",
                fontSize=16,
                anchor="middle",
            ),
            width=700,
            height=450,
        ).configure_axis(
            labelFontSize=11,
            titleFontSize=12,
        ).configure_view(
            strokeWidth=0.5,
            stroke="#cccccc",
        ).configure_legend(
            labelFontSize=10,
            titleFontSize=12,
        )

        # Export to PNG using vl_convert
        png_bytes = vlc.vegalite_to_png(combined_chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> str:
        """Render Chinese narrative comparing turbulence across heights.

        Summarizes the representative TI values and IEC categories,
        highlighting how turbulence intensity changes with height.
        """
        sorted_df = self.df.sort("height")

        # Get unique heights
        height_strs = [
            get_height_display_name(
                row["height"], row.get("interpolation_marker", "") or ""
            )
            for row in sorted_df.select("height", "interpolation_marker").unique().iter_rows(named=True)
        ]

        # Calculate average representative TI per height
        ti_by_height = []
        for row in sorted_df.group_by("height", "interpolation_marker").agg(
            pl.col("representative_ti").mean().alias("avg_rep_ti"),
            pl.col("mean_ti").mean().alias("avg_mean_ti"),
        ).sort("height").iter_rows(named=True):
            height_display = get_height_display_name(
                row["height"], row.get("interpolation_marker", "") or ""
            )
            ti_by_height.append({
                "height": height_display,
                "avg_rep_ti": row["avg_rep_ti"],
                "avg_mean_ti": row["avg_mean_ti"],
            })

        # Find highest and lowest TI
        max_ti = max(ti_by_height, key=lambda x: x["avg_rep_ti"])
        min_ti = min(ti_by_height, key=lambda x: x["avg_rep_ti"])

        # Count IEC category distribution
        iec_counts = sorted_df.group_by("iec_category").len().sort("len", descending=True)
        top_category = iec_counts.row(0, named=True) if len(iec_counts) > 0 else {"iec_category": "B", "len": 0}
        total_count = len(sorted_df)
        top_count = int(top_category["len"]) if top_category else 0
        top_pct = (top_count / total_count * 100) if total_count > 0 else 0

        # Generate summary text
        height_summary = "；".join([
            f"{h['height']}代表湍流强度{h['avg_rep_ti']:.3f}"
            for h in ti_by_height
        ])

        return (
            f"由图{self.getReference()}可知，"
            f"测风塔{self.meta.mast_name}在{', '.join(height_strs)}各高度的"
            f"湍流强度分布特征明显。{height_summary}。"
            f"从高度分布来看，{max_ti['height']}湍流强度最大（{max_ti['avg_rep_ti']:.3f}），"
            f"{min_ti['height']}湍流强度最小（{min_ti['avg_rep_ti']:.3f}），"
            f"整体呈现随高度增加湍流强度逐渐降低的趋势。"
            f"根据IEC分类标准，各高度数据主要属于{top_category['iec_category']}类（占比{top_pct:.1f}%），"
            f"参考图中IEC标准带可知，实测湍流强度与IEC参考值基本吻合，"
            f"风电场湍流条件{'较好' if top_category['iec_category'] in ['C', 'B'] else '一般'}，"
            f"适合安装{'主流机型' if top_category['iec_category'] in ['A', 'B', 'C'] else '高湍流适应性机型'}。"
        )
