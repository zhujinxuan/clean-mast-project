"""Wind range summary atom for single mast analysis (productive range 3-25 m/s).

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path

import polars as pl
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
class SingleMastWindRangeSummaryAtom(ReportAtom[WindFrequencySchema, SingleMastMeta]):
    """Renders productive wind range (3-25 m/s) summary table per height.

    This range represents the typical turbine operating range (cut-in ~3 m/s, cut-out ~25 m/s).

    - Table: Height, 3-25m/s frequency, 3-25m/s hours, wind power frequency, wind power hours
    - Image: No image for summary (returns empty Path)
    - Summary: Chinese description of productivity assessment
    """

    @override
    def renderTable(self) -> str:
        """Render as Typst table with 3-25 m/s productive range summary by height.

        Columns: 高度 | 3-25m/s频率 | 3-25m/s小时数 | 风能频率 | 风能小时数
        """
        productive_df = self.df.filter(
            (pl.col("bin_start") >= 3.0) & (pl.col("bin_end") <= 25.0)
        )

        summary_df = productive_df.group_by(["height", "interpolation_marker"]).agg(
            [
                pl.col("frequency").sum().alias("frequency_sum"),
                pl.col("power_frequency").sum().alias("power_frequency_sum"),
            ]
        )

        hours_per_year = 8760.0
        summary_df = summary_df.with_columns(
            [
                (pl.col("frequency_sum") * hours_per_year).alias("hours"),
                (pl.col("power_frequency_sum") * hours_per_year).alias("power_hours"),
            ]
        )

        sorted_df = summary_df.sort("height")

        rows = []
        for row in sorted_df.iter_rows(named=True):
            height_display = get_height_display_name(row["height"], row["interpolation_marker"] or "")
            freq_pct = row["frequency_sum"] * 100
            hours = row["hours"]
            power_freq_pct = row["power_frequency_sum"] * 100
            power_hrs = row["power_hours"]
            rows.append(
                f"  [{height_display}], [{freq_pct:.1f}%], [{hours:.0f}], [{power_freq_pct:.1f}%], [{power_hrs:.0f}],"
            )

        return f"""#table(
  columns: (auto, auto, auto, auto, auto),
  inset: 8pt,
  align: center,
  table.header(
    [高度], [3-25m/s频率], [3-25m/s小时数], [风能频率], [风能小时数]
  ),
{chr(10).join(rows)}
)
"""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image generation for wind range summary.

        Wind range summary is displayed as a table only.
        Returns a placeholder Path.
        """
        return Path()

    @override
    def renderSummary(self) -> str:
        """Generate Chinese summary of productive wind range (3-25 m/s) assessment."""
        productive_df = self.df.filter(
            (pl.col("bin_start") >= 3.0) & (pl.col("bin_end") <= 25.0)
        )

        summary_df = productive_df.group_by(["height", "interpolation_marker"]).agg(
            [
                pl.col("frequency").sum().alias("frequency_sum"),
                pl.col("power_frequency").sum().alias("power_frequency_sum"),
            ]
        )

        hours_per_year = 8760.0
        summary_df = summary_df.with_columns(
            [
                (pl.col("frequency_sum") * hours_per_year).alias("hours"),
                (pl.col("power_frequency_sum") * hours_per_year).alias("power_hours"),
            ]
        )

        sorted_df = summary_df.sort("height")

        heights = sorted_df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_strs = [
            get_height_display_name(row["height"], row["interpolation_marker"] or "")
            for row in heights.iter_rows(named=True)
        ]

        from typing import cast
        avg_freq = float(cast(float, sorted_df["frequency_sum"].mean()) or 0)
        avg_hours = float(cast(float, sorted_df["hours"].mean()) or 0)
        avg_power_freq = float(cast(float, sorted_df["power_frequency_sum"].mean()) or 0)
        avg_power_hours = float(cast(float, sorted_df["power_hours"].mean()) or 0)

        best_row = sorted_df.sort("hours", descending=True).row(0, named=True)
        best_height = get_height_display_name(best_row["height"], best_row["interpolation_marker"] or "")
        best_hours = best_row["hours"]
        best_freq = best_row["frequency_sum"] * 100

        if avg_freq >= 0.60:
            productivity = "优秀"
            recommendation = "风能资源非常丰富，适合安装大容量风电机组"
        elif avg_freq >= 0.45:
            productivity = "良好"
            recommendation = "风能资源丰富，具备良好的开发价值"
        elif avg_freq >= 0.30:
            productivity = "一般"
            recommendation = "风能资源中等，需结合经济性评估"
        else:
            productivity = "较差"
            recommendation = "风能资源相对匮乏，开发需谨慎评估"

        return (
            f"{self.meta.mast_name}测风塔有效风速区间(3-25m/s)分析汇总。"
            f"分析高度包括{', '.join(height_strs)}。"
            f"各高度平均有效风速频率为{avg_freq * 100:.1f}%，"
            f"对应年有效小时数约{avg_hours:.0f}小时。"
            f"风能频率平均{avg_power_freq * 100:.1f}%，"
            f"风能小时数约{avg_power_hours:.0f}小时。"
            f"最优高度为{best_height}，"
            f"有效风速频率{best_freq:.1f}%，年有效小时数{best_hours:.0f}小时。"
            f"整体资源等级评定为{productivity}，{recommendation}。"
        )
