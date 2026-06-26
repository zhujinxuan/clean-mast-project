"""Fifty-year max wind Method 1 atom for reporting domain.

LOGIC-PRESERVATION: Ported from assessment
entities/fifty_year_max_wind_method1_atom.py.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import polars as pl
from typing_extensions import override

from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.model import get_height_display_name
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.report_meta import (
    ExtremeWindAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.schemas import (
    FiftyYearMaxWindMethod1DetailSchema,
)


@dataclass(frozen=True)
class Method1Atom(ReportAtom[FiftyYearMaxWindMethod1DetailSchema, ExtremeWindAtomMeta]):
    """Renders fifty-year max wind Method 1 (五倍风速法) table and summary.

    - Table: Height, sustained wind speed, standard-density sustained,
             extreme wind speed, standard-density extreme
    - Image: No image for Method 1 (returns None)
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
        if self.df.is_empty():
            return TypstTable(
                headers=[
                    "高度(m)", "50年最大持续风速(m/s)", "标准密度持续风速(m/s)",
                    "50年极大极端风速(m/s)", "标准密度极端风速(m/s)",
                ],
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
            height_display = get_height_display_name(
                cast(float, row["height"]),
                cast(str, row["interpolation_marker"] or ""),
            )
            rows.append([
                height_display,
                f"{row['max_wind_speed']:.2f}",
                f"{row['standard_density_wind_speed']:.2f}",
                f"{row['max_wind_speed_extreme']:.2f}",
                f"{row['standard_density_wind_speed_extreme']:.2f}",
            ])

        return TypstTable(
            headers=[
                "高度(m)", "50年最大持续风速(m/s)", "标准密度持续风速(m/s)",
                "50年极大极端风速(m/s)", "标准密度极端风速(m/s)",
            ],
            data=rows,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        if self.df.is_empty():
            return [TypstParagraph(text=f"{self.meta.mast_name}测风塔暂无有效的五倍风速法分析数据。")]

        avg_density = self.df["air_density"].mean()
        sustained_df = self.df.filter(pl.col("wind_speed_type") == "sustained").sort("height")

        height_parts = []
        for row in sustained_df.iter_rows(named=True):
            height_display = get_height_display_name(
                cast(float, row["height"]),
                cast(str, row["interpolation_marker"] or ""),
            )
            sustained = cast(float, row["max_wind_speed"])
            sustained_std = cast(float, row["standard_density_wind_speed"])
            avg_speed = cast(float, row["average_wind_speed"])
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
