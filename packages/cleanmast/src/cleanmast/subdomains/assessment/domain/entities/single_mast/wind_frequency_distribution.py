"""Wind frequency distribution atom for single mast analysis.

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
    WindFrequencySchema,
)


@dataclass
class SingleMastWindFrequencyDistributionAtom(ReportAtom[WindFrequencySchema, SingleMastMeta]):
    """Renders wind frequency vs power frequency distribution - grouped bar chart per height.

    - Table: Empty (chart only visualization)
    - Image: Grouped bar chart per height comparing frequency vs power_frequency
    - Summary: Chinese description of distribution shape and wind energy characteristics
    """

    @override
    def renderTable(self) -> str:
        """Return empty string - visualization is chart only."""
        return ""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """Generate grouped bar chart comparing speed freq vs power freq - one per height.

        Each chart shows:
        - Grouped bars for frequency and power_frequency side by side
        - X-axis: wind speed bin center
        - Different colors for each metric with legend

        Uses Altair with xOffset for side-by-side bars, exports via vl-convert.
        """
        cache_key = self.get_or_compute_df_hashkey()
        image_path = output_dir / f"wind_freq_dist_{self.meta.mast_name}_{cache_key}.png"

        if not force and image_path.exists():
            return image_path

        # Build charts for each height
        charts = []
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")

        for row in heights_df.iter_rows(named=True):
            height = row["height"]
            marker = row["interpolation_marker"]
            display = get_height_display_name(height, marker)

            # Get data for this height and create melted DataFrame
            height_df = self.df.filter(pl.col("height") == height).sort("bin_center")

            # Melt data to long format for grouped bars
            df_melted = height_df.select([
                "bin_center",
                "frequency",
                "power_frequency",
            ]).unpivot(
                index=["bin_center"],
                on=["frequency", "power_frequency"],
                variable_name="metric",
                value_name="value",
            ).to_pandas()

            # Create grouped bar chart
            chart = alt.Chart(df_melted).mark_bar(width=8).encode(
                x=alt.X("bin_center:Q", title="风速 (m/s)"),
                xOffset=alt.XOffset("metric:N", title=None),
                y=alt.Y("value:Q", title="频率", axis=alt.Axis(format=".2%")),
                color=alt.Color(
                    "metric:N",
                    title="类型",
                    scale=alt.Scale(
                        domain=["frequency", "power_frequency"],
                        range=["#1f77b4", "#ff7f0e"],
                    ),
                    legend=alt.Legend(
                        title="频率类型",
                        labelExpr="datum.value == 'frequency' ? '风速频率' : '风能频率'",
                    ),
                ),
                tooltip=[
                    alt.Tooltip("bin_center:Q", title="风速(m/s)", format=".1f"),
                    alt.Tooltip("value:Q", title="频率", format=".2%"),
                    alt.Tooltip("metric:N", title="类型"),
                ],
            ).properties(
                title=f"{display} 风频与风能分布",
                width=450,
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
                title=f"{self.meta.mast_name} 风频与风能分布"
            )

        # Export to PNG
        output_dir.mkdir(parents=True, exist_ok=True)
        png_bytes = vlc.vegalite_to_png(final_chart.to_dict(), scale=2.0)
        image_path.write_bytes(png_bytes)

        return image_path

    @override
    def renderSummary(self) -> str:
        """Generate Chinese summary of wind frequency distribution shape."""
        # Get unique heights
        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_strs = [
            get_height_display_name(row["height"], row["interpolation_marker"])
            for row in heights_df.iter_rows(named=True)
        ]

        # Analyze distribution characteristics per height
        analyses = []
        for row in heights_df.iter_rows(named=True):
            height = row["height"]
            marker = row["interpolation_marker"]
            display = get_height_display_name(height, marker)

            # Get data for this height
            height_df = self.df.filter(pl.col("height") == height)

            # Find peak frequency bin
            peak_freq_idx = height_df["frequency"].arg_max()
            peak_freq_row = height_df.row(peak_freq_idx, named=True)
            peak_freq_speed = peak_freq_row["bin_center"]
            peak_freq_value = peak_freq_row["frequency"]

            # Find peak power frequency bin
            peak_power_idx = height_df["power_frequency"].arg_max()
            peak_power_row = height_df.row(peak_power_idx, named=True)
            peak_power_speed = peak_power_row["bin_center"]
            peak_power_value = peak_power_row["power_frequency"]

            # Calculate mean speed (approximation using bin centers)
            total_freq = height_df["frequency"].sum()
            mean_speed = float((height_df["bin_center"] * height_df["frequency"]).sum()) / float(total_freq)

            # Calculate energy-weighted mean speed
            total_power_freq = height_df["power_frequency"].sum()
            energy_weighted_speed = float((
                height_df["bin_center"] * height_df["power_frequency"]
            ).sum()) / float(total_power_freq)

            # Distribution shape analysis
            # Find where power_frequency exceeds frequency (wind energy rich region)
            wind_rich = height_df.filter(pl.col("power_frequency") > pl.col("frequency"))
            if len(wind_rich) > 0:
                wind_rich_start = wind_rich["bin_center"].min()
                wind_rich_end = wind_rich["bin_center"].max()
            else:
                wind_rich_start = None
                wind_rich_end = None

            analyses.append({
                "display": display,
                "peak_freq_speed": peak_freq_speed,
                "peak_freq_value": peak_freq_value,
                "peak_power_speed": peak_power_speed,
                "peak_power_value": peak_power_value,
                "mean_speed": mean_speed,
                "energy_weighted_speed": energy_weighted_speed,
                "wind_rich_start": wind_rich_start,
                "wind_rich_end": wind_rich_end,
            })

        # Build summary text
        if len(analyses) == 1:
            a = analyses[0]
            wind_rich_text = ""
            if a["wind_rich_start"] is not None:
                wind_rich_text = (
                    f"风能频率占优区间为{a['wind_rich_start']:.1f}~{a['wind_rich_end']:.1f}m/s，"
                )

            return (
                f"{self.meta.mast_name}测风塔{a['display']}风频与风能分布分析。"
                f"风速频率峰值出现在{a['peak_freq_speed']:.1f}m/s处(频率{a['peak_freq_value']:.1%})，"
                f"风能频率峰值出现在{a['peak_power_speed']:.1f}m/s处(频率{a['peak_power_value']:.1%})。"
                f"平均风速为{a['mean_speed']:.2f}m/s，"
                f"能量加权平均风速为{a['energy_weighted_speed']:.2f}m/s，"
                f"后者较前者高{a['energy_weighted_speed']-a['mean_speed']:.2f}m/s，"
                f"反映风能主要集中在较高风速区间。"
                f"{wind_rich_text}"
                f"该分布特征可用于风电机组选型和风能资源评估。"
            )
        else:
            # Multiple heights - provide comparison summary
            summary_parts = [
                f"{self.meta.mast_name}测风塔各高度层风频与风能分布分析。"
                f"分析高度包括{', '.join(height_strs)}。"
            ]

            for a in analyses:
                wind_rich_text = ""
                if a["wind_rich_start"] is not None:
                    wind_rich_text = (
                        f"风能占优区间{a['wind_rich_start']:.0f}~{a['wind_rich_end']:.0f}m/s，"
                    )

                summary_parts.append(
                    f"{a['display']}:风速频率峰值{a['peak_freq_speed']:.1f}m/s({a['peak_freq_value']:.1%})，"
                    f"风能频率峰值{a['peak_power_speed']:.1f}m/s({a['peak_power_value']:.1%})，"
                    f"平均风速{a['mean_speed']:.2f}m/s，"
                    f"能量加权风速{a['energy_weighted_speed']:.2f}m/s。"
                    f"{wind_rich_text}"
                )

            # Compare heights
            if len(analyses) >= 2:
                speeds = [a["mean_speed"] for a in analyses]
                speed_diff = max(speeds) - min(speeds)
                summary_parts.append(
                    f"各高度层平均风速差异为{speed_diff:.2f}m/s，"
                    f"风能分布特征基本一致，风能均主要集中于中高风速区间。"
                )

            summary_parts.append("该分布特征为风电机组选型和发电量估算提供依据。")

            return "".join(summary_parts)
