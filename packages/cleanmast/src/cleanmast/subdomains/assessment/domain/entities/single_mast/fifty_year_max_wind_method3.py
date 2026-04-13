"""Fifty-year max wind Method 3 atom for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path

import polars as pl
from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.types import (
    TypstParagraph,
    TypstTable,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
    get_height_display_name,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    FiftyYearMaxWindResultSchema,
)

_WIND_SPEED_TYPE_LABELS = {
    "sustained": "持续风速",
    "extreme": "极端风速",
}


@dataclass
class SingleMastFiftyYearMaxWindMethod3Atom(
    ReportAtom[FiftyYearMaxWindResultSchema, SingleMastMeta]
):
    """Renders fifty-year max wind Method 3 (极端风速模型法) table and summary.

    - Table: Height, wind speed type, observed max, 50-year max, standard-density max
    - Image: No image for Method 3 (returns empty Path)
    - Summary: Chinese description of results per height
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} 极端风速模型法结果"

    @override
    def renderTable(self) -> TypstTable | None:
        """Render as Typst table with Method 3 results in long format."""
        if self.df.is_empty():
            return TypstTable(
                headers=["高度(m)", "风速类型", "观测最大值(m/s)", "50年重现期风速(m/s)", "标准密度风速(m/s)"],
                data=[],
                caption=self._resolve_table_caption(),
            )

        sorted_df = self.df.sort(["height", "wind_speed_type"])

        rows = []
        for row in sorted_df.iter_rows(named=True):
            height_display = get_height_display_name(row["height"], row["interpolation_marker"] or "")
            ws_type_label = _WIND_SPEED_TYPE_LABELS.get(row["wind_speed_type"], row["wind_speed_type"])
            observed_max = row["observed_max"] or 0.0
            rows.append([
                height_display,
                ws_type_label,
                f"{observed_max:.2f}",
                f"{row['max_wind_speed']:.2f}",
                f"{row['standard_density_wind_speed']:.2f}",
            ])

        return TypstTable(
            headers=["高度(m)", "风速类型", "观测最大值(m/s)", "50年重现期风速(m/s)", "标准密度风速(m/s)"],
            data=rows,
            caption=self._resolve_table_caption(),
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image generation for Method 3."""
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """Generate Chinese summary of Method 3 results."""
        if self.df.is_empty():
            return [TypstParagraph(text=f"{self.meta.mast_name}测风塔暂无有效的极端风速模型法分析数据。")]

        sustained_df = self.df.filter(pl.col("wind_speed_type") == "sustained").sort("height")

        height_parts = []
        for row in sustained_df.iter_rows(named=True):
            height_display = get_height_display_name(row["height"], row["interpolation_marker"] or "")
            observed_max = row["observed_max"] or 0.0
            v50 = row["max_wind_speed"]
            v50_std = row["standard_density_wind_speed"]
            height_parts.append(
                f"{height_display}:观测最大值{observed_max:.2f}m/s,"
                f"50年重现期风速{v50:.2f}m/s(标准密度{v50_std:.2f}m/s)"
            )

        text = (
            f"{self.meta.mast_name}测风塔五十年一遇最大风速估算(方法三:极端风速模型法)。"
            f"基于观测期内各高度最大风速的1.25倍估算50年重现期风速。"
            f"各高度结果如下：{'；'.join(height_parts)}。"
        )
        return [TypstParagraph(text=text)]
