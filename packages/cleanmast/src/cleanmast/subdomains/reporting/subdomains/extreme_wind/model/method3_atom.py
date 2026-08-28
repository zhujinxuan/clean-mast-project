"""Fifty-year max wind Method 3 atom for reporting domain.

LOGIC-PRESERVATION: Ported from assessment
entities/fifty_year_max_wind_method3_atom.py.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import polars as pl
from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.model import get_height_display_name
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.report_meta import (
    ExtremeWindAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.schemas import (
    FiftyYearMaxWindResultSchema,
)

_WIND_SPEED_TYPE_LABELS = {
    "sustained": "持续风速",
    "extreme": "极端风速",
}


@dataclass(frozen=True)
class Method3Atom(ReportAtom[FiftyYearMaxWindResultSchema, ExtremeWindAtomMeta]):
    """Renders fifty-year max wind Method 3 (极端风速模型法) table and summary."""

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
        if self.df.is_empty():
            return TypstTable(
                headers=["高度(m)", "风速类型", "观测最大值(m/s)", "50年重现期风速(m/s)", "标准密度风速(m/s)"],
                data=[],
                caption=self.default_table_caption,
            )

        sorted_df = self.df.sort(["height", "wind_speed_type"])

        rows = []
        for row in sorted_df.iter_rows(named=True):
            marker = cast(str, row["interpolation_marker"] or "")
            height_display = get_height_display_name(cast(float, row["height"]), marker)
            ws_type_label = _WIND_SPEED_TYPE_LABELS.get(
                cast(str, row["wind_speed_type"]),
                cast(str, row["wind_speed_type"]),
            )
            observed_max = cast(float, row["observed_max"] or 0.0)
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
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        if self.df.is_empty():
            return [TypstParagraph(text=f"{self.meta.mast_name}测风塔暂无有效的极端风速模型法分析数据。")]

        sustained_df = self.df.filter(pl.col("wind_speed_type") == "sustained").sort("height")

        height_parts = []
        for row in sustained_df.iter_rows(named=True):
            marker = cast(str, row["interpolation_marker"] or "")
            height_display = get_height_display_name(cast(float, row["height"]), marker)
            observed_max = cast(float, row["observed_max"] or 0.0)
            v50 = cast(float, row["max_wind_speed"])
            v50_std = cast(float, row["standard_density_wind_speed"])
            height_parts.append(
                f"{height_display}:观测最大值{observed_max:.2f}m/s,"
                f"50年重现期风速{v50:.2f}m/s(标准密度{v50_std:.2f}m/s)"
            )
        text = (
            f"{self.meta.mast_name}测风塔五十年一遇最大风速估算(方法三:极端风速模型法)。"
            f"基于观测期内各高度最大风速的1.25倍估算50年重现期风速。"
        )
        if height_parts:
            text += f"各高度结果如下：{'；'.join(height_parts)}。"

        return [TypstParagraph(text=text)]
