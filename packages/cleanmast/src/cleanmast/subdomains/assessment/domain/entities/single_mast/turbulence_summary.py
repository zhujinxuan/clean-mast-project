"""Turbulence summary atom for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import polars as pl
from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
    get_height_display_name,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TurbulenceSchema,
)


@dataclass
class SingleMastTurbulenceSummaryAtom(ReportAtom[TurbulenceSchema, SingleMastMeta]):
    """Renders turbulence intensity summary table per height.

    - Table: Height, wind speed range, mean TI, representative TI, IEC category
    - Image: No image for summary (returns empty Path)
    - Summary: Chinese description of turbulence classification results
    """

    @override
    def renderTable(self) -> str:
        """Render as Typst table with turbulence summary by height.

        Columns: 高度 | 风速范围(m/s) | 平均湍流强度 | 代表湍流强度 | IEC类别
        """
        # Aggregate per height: wind range, mean TI, rep TI, IEC category
        summary_df = self.df.group_by(["height", "interpolation_marker"]).agg(
            [
                pl.col("wind_speed_bin").min().alias("min_speed"),
                pl.col("wind_speed_bin").max().alias("max_speed"),
                pl.col("mean_ti").mean().alias("mean_ti"),
                pl.col("representative_ti").mean().alias("representative_ti"),
                # Most frequent IEC category per height
                pl.col("iec_category")
                .filter(
                    pl.col("iec_category").is_not_null() & (pl.col("iec_category") != "")
                )
                .mode()
                .first()
                .alias("iec_category"),
            ]
        )

        # Sort by height for consistent display
        sorted_df = summary_df.sort("height")

        # Build table rows
        rows = []
        for row in sorted_df.iter_rows(named=True):
            height_display = get_height_display_name(row["height"], row["interpolation_marker"] or "")
            wind_range = f"{row['min_speed']}-{row['max_speed']}"
            mean_ti = row["mean_ti"]
            rep_ti = row["representative_ti"]
            iec_cat = row["iec_category"] or "-"
            rows.append(
                f"  [{height_display}], [{wind_range}], [{mean_ti:.3f}], [{rep_ti:.3f}], [{iec_cat}],"
            )

        return f"""#table(
  columns: (auto, auto, auto, auto, auto),
  inset: 8pt,
  align: center,
  table.header(
    [高度], [风速范围(m/s)], [平均湍流强度], [代表湍流强度], [IEC类别]
  ),
{chr(10).join(rows)}
)
"""

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image generation for turbulence summary.

        Turbulence summary is displayed as a table only.
        Returns a placeholder Path.
        """
        # No image needed for turbulence summary
        return Path()

    @override
    def renderSummary(self) -> str:
        """Generate Chinese summary of turbulence intensity classification results."""
        # Aggregate per height for summary
        summary_df = self.df.group_by(["height", "interpolation_marker"]).agg(
            [
                pl.col("mean_ti").mean().alias("mean_ti"),
                pl.col("representative_ti").mean().alias("representative_ti"),
                pl.col("iec_category")
                .filter(
                    pl.col("iec_category").is_not_null() & (pl.col("iec_category") != "")
                )
                .mode()
                .first()
                .alias("iec_category"),
            ]
        )

        sorted_df = summary_df.sort("height")

        # Get unique heights for mention
        heights = sorted_df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_strs = [
            get_height_display_name(row["height"], row["interpolation_marker"] or "")
            for row in heights.iter_rows(named=True)
        ]

        # Calculate summary statistics
        _mean_ti_val = cast(float | None, sorted_df["mean_ti"].mean())
        _rep_ti_val = cast(float | None, sorted_df["representative_ti"].mean())
        avg_mean_ti = float(_mean_ti_val or 0)
        avg_rep_ti = float(_rep_ti_val or 0)

        # Handle empty DataFrame case
        if sorted_df.is_empty():
            return (
                f"{self.meta.mast_name}测风塔暂无有效的湍流强度数据可供分析。"
            )

        # Find extreme values
        max_ti_row = sorted_df.sort("mean_ti", descending=True).row(0, named=True)
        min_ti_row = sorted_df.sort("mean_ti", descending=False).row(0, named=True)

        # Count IEC categories
        iec_counts = sorted_df.group_by("iec_category").len().sort("len", descending=True)
        iec_summary_parts = []
        for iec_row in iec_counts.iter_rows(named=True):
            cat = iec_row["iec_category"] or "未分类"
            count = iec_row["len"]
            iec_summary_parts.append(f"{cat}类({count}个高度)")

        iec_summary = "、".join(iec_summary_parts) if iec_summary_parts else "无有效分类"

        return (
            f"{self.meta.mast_name}测风塔湍流强度分析汇总。"
            f"分析高度包括{', '.join(height_strs)}。"
            f"各高度平均湍流强度为{avg_mean_ti:.3f}，"
            f"平均代表湍流强度(P90)为{avg_rep_ti:.3f}。"
            f"湍流强度最大值{max_ti_row['mean_ti']:.3f}出现在"
            f"{get_height_display_name(max_ti_row['height'], max_ti_row['interpolation_marker'] or '')}，"
            f"最小值{min_ti_row['mean_ti']:.3f}出现在"
            f"{get_height_display_name(min_ti_row['height'], min_ti_row['interpolation_marker'] or '')}。"
            f"按IEC标准分类：{iec_summary}。"
            f"整体湍流水平{'较高' if avg_mean_ti > 0.15 else '中等' if avg_mean_ti > 0.12 else '较低'}，"
            f"{'建议选用更高等级机组' if avg_mean_ti > 0.16 else '适合常规机组选型'}。"
        )
