"""Fifty-year max wind Method 1 atom for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path

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
from cleanmast.subdomains.assessment.subdomains.extreme_wind.value_objects.schemas import (
    FiftyYearMaxWindMethod1DetailSchema,
)


@dataclass
class SingleMastFiftyYearMaxWindMethod1Atom(
    ReportAtom[FiftyYearMaxWindMethod1DetailSchema, SingleMastMeta]
):
    """Renders fifty-year max wind Method 1 (五倍风速法) table and summary.

    - Table: Height, sustained wind speed, standard-density sustained,
             extreme wind speed, standard-density extreme
    - Image: No image for Method 1 (returns empty Path)
    - Summary: Chinese description of results per height
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} 五倍平均风速法估算结果"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render as Typst table with Method 1 results by height.

        Columns: 高度(m) | 50年最大持续风速(m/s) | 标准密度持续风速(m/s) |
                 50年极大极端风速(m/s) | 标准密度极端风速(m/s)
        """
        if self.df.is_empty():
            return TypstTable(
                headers=["高度(m)", "50年最大持续风速(m/s)", "标准密度持续风速(m/s)", "50年极大极端风速(m/s)", "标准密度极端风速(m/s)"],
                data=[],
                caption=self.default_table_caption,
            )

        sustained_df = self.df.filter(pl.col("wind_speed_type") == "sustained").select(
            ["height", "interpolation_marker", "max_wind_speed", "standard_density_wind_speed"]
        )
        extreme_df = self.df.filter(pl.col("wind_speed_type") == "extreme").select(
            ["height", "max_wind_speed", "standard_density_wind_speed"]
        )

        joined = sustained_df.join(extreme_df, on="height", suffix="_extreme").sort("height")

        rows = []
        for row in joined.iter_rows(named=True):
            height_display = get_height_display_name(row["height"], row["interpolation_marker"] or "")
            rows.append([
                height_display,
                f"{row['max_wind_speed']:.2f}",
                f"{row['standard_density_wind_speed']:.2f}",
                f"{row['max_wind_speed_extreme']:.2f}",
                f"{row['standard_density_wind_speed_extreme']:.2f}",
            ])

        return TypstTable(
            headers=["高度(m)", "50年最大持续风速(m/s)", "标准密度持续风速(m/s)", "50年极大极端风速(m/s)", "标准密度极端风速(m/s)"],
            data=rows,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image generation for Method 1."""
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """Generate Chinese summary of Method 1 results."""
        if self.df.is_empty():
            return [TypstParagraph(text=f"{self.meta.mast_name}测风塔暂无有效的五倍风速法分析数据。")]

        # Average air density across all rows
        avg_density = self.df["air_density"].mean()

        # Build per-height summary strings from sustained rows
        sustained_df = self.df.filter(pl.col("wind_speed_type") == "sustained").sort("height")

        height_parts = []
        for row in sustained_df.iter_rows(named=True):
            height_display = get_height_display_name(row["height"], row["interpolation_marker"] or "")
            sustained = row["max_wind_speed"]
            sustained_std = row["standard_density_wind_speed"]
            avg_speed = row["average_wind_speed"]
            height_parts.append(
                f"{height_display}:平均风速{avg_speed:.2f}m/s,"
                f"50年最大持续风速{sustained:.2f}m/s(标准密度{sustained_std:.2f}m/s)"
            )

        text = (
            f"{self.meta.mast_name}测风塔五十年一遇最大风速估算(方法一:五倍平均风速法)。"
            f"基于IEC 61400-1标准，以多年平均风速的5倍作为50年最大持续风速，"
            f"极大风速按持续风速的1.4倍计算。"
            f"平均空气密度约为{avg_density:.3f}kg/m³。"
            f"各高度结果如下：{'；'.join(height_parts)}。"
        )
        return [TypstParagraph(text=text)]
