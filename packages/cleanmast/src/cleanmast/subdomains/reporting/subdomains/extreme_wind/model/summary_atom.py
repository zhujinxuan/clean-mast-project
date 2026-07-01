"""Fifty-year max wind summary atoms for reporting domain.

LOGIC-PRESERVATION: Ported from assessment
entities/fifty_year_max_wind_summary_atom.py.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.model import get_height_display_name
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.report_meta import (
    ExtremeWindAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.schemas import (
    FiftyYearMaxWindComparisonSchema,
    IECWindClassSchema,
)


@dataclass(frozen=True)
class ComparisonSustainedAtom(ReportAtom[FiftyYearMaxWindComparisonSchema, ExtremeWindAtomMeta]):
    """Renders fifty-year max wind sustained comparison across methods."""

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} 五十年一遇持续风速多方法对比"

    @override
    def renderTable(self) -> TypstTable | None:
        if self.df.is_empty():
            return TypstTable(
                headers=["高度(m)", "5倍平均风速法(m/s)", "五日最大风速法(m/s)", "极端风速模型法(m/s)", "保守估计(m/s)"],
                data=[],
                caption=self.default_table_caption,
            )

        sorted_df = self.df.sort("height")
        rows = []
        for row in sorted_df.iter_rows(named=True):
            marker = cast(str, row.get("interpolation_marker") or "")
            height_display = get_height_display_name(cast(float, row["height"]), marker)
            rows.append([
                height_display,
                _format_value(cast(float, row["method1"])),
                _format_value(cast(float, row["method2"])),
                _format_value(cast(float, row["method3"])),
                _format_value(cast(float, row["conservative_max"])),
            ])

        return TypstTable(
            headers=["高度(m)", "5倍平均风速法(m/s)", "五日最大风速法(m/s)", "极端风速模型法(m/s)", "保守估计(m/s)"],
            data=rows,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        if self.df.is_empty():
            return [TypstParagraph(text=f"{self.meta.mast_name}测风塔暂无有效的五十年一遇持续风速对比数据。")]

        sorted_df = self.df.sort("height")
        height_parts = []
        for row in sorted_df.iter_rows(named=True):
            marker = cast(str, row.get("interpolation_marker") or "")
            height_display = get_height_display_name(cast(float, row["height"]), marker)
            parts = []
            if row["method1"]:
                parts.append(f"五倍平均风速法{row['method1']:.2f}m/s")
            if row["method2"]:
                parts.append(f"五日最大风速法{row['method2']:.2f}m/s")
            if row["method3"]:
                parts.append(f"极端风速模型法{row['method3']:.2f}m/s")
            if parts:
                height_parts.append(f"{height_display}:" + "、".join(parts))

        text = (
            f"{self.meta.mast_name}测风塔五十年一遇最大持续风速多方法对比结果。"
            f"各高度结果如下：{'；'.join(height_parts)}。"
        )
        return [TypstParagraph(text=text)]


@dataclass(frozen=True)
class ComparisonExtremeAtom(ReportAtom[FiftyYearMaxWindComparisonSchema, ExtremeWindAtomMeta]):
    """Renders fifty-year max wind extreme comparison across methods."""

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} 五十年一遇极端风速多方法对比"

    @override
    def renderTable(self) -> TypstTable | None:
        if self.df.is_empty():
            return TypstTable(
                headers=["高度(m)", "5倍平均风速法(m/s)", "五日最大风速法(m/s)", "极端风速模型法(m/s)", "保守估计(m/s)"],
                data=[],
                caption=self.default_table_caption,
            )

        sorted_df = self.df.sort("height")
        rows = []
        for row in sorted_df.iter_rows(named=True):
            marker = cast(str, row.get("interpolation_marker") or "")
            height_display = get_height_display_name(cast(float, row["height"]), marker)
            rows.append([
                height_display,
                _format_value(cast(float, row["method1"])),
                _format_value(cast(float, row["method2"])),
                _format_value(cast(float, row["method3"])),
                _format_value(cast(float, row["conservative_max"])),
            ])

        return TypstTable(
            headers=["高度(m)", "5倍平均风速法(m/s)", "五日最大风速法(m/s)", "极端风速模型法(m/s)", "保守估计(m/s)"],
            data=rows,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        if self.df.is_empty():
            return [TypstParagraph(text=f"{self.meta.mast_name}测风塔暂无有效的五十年一遇极端风速对比数据。")]

        sorted_df = self.df.sort("height")
        height_parts = []
        for row in sorted_df.iter_rows(named=True):
            marker = cast(str, row.get("interpolation_marker") or "")
            height_display = get_height_display_name(cast(float, row["height"]), marker)
            parts = []
            if row["method1"]:
                parts.append(f"五倍平均风速法{row['method1']:.2f}m/s")
            if row["method2"]:
                parts.append(f"五日最大风速法{row['method2']:.2f}m/s")
            if row["method3"]:
                parts.append(f"极端风速模型法{row['method3']:.2f}m/s")
            if parts:
                height_parts.append(f"{height_display}:" + "、".join(parts))

        text = (
            f"{self.meta.mast_name}测风塔五十年一遇极大极端风速多方法对比结果。"
            f"各高度结果如下：{'；'.join(height_parts)}。"
        )
        return [TypstParagraph(text=text)]


@dataclass(frozen=True)
class IECWindClassAtom(ReportAtom[IECWindClassSchema, ExtremeWindAtomMeta]):
    """Renders IEC wind class reference table."""

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} IEC风区等级分类"

    @override
    def renderTable(self) -> TypstTable | None:
        if self.df.is_empty():
            return TypstTable(
                headers=["高度(m)", "风区等级", "最大持续风速Vref(m/s)", "极大极端风速Ve50(m/s)"],
                data=[],
                caption=self.default_table_caption,
            )

        rows = []
        for row in self.df.iter_rows(named=True):
            wind_class = cast(str, row["wind_class"])
            height = row.get("height")

            if height is None:
                if wind_class == "S":
                    rows.append(["—", "S类", "场址专用", "场址专用"])
                else:
                    rows.append([
                        "—",
                        f"{wind_class}类",
                        f"{row['sustained_threshold']:.1f}",
                        f"{row['extreme_threshold']:.1f}",
                    ])
            else:
                sustained = row.get("conservative_sustained")
                extreme = row.get("conservative_extreme")
                rows.append([
                    f"{float(height):.1f}",
                    f"{wind_class}类",
                    f"{sustained:.2f}" if sustained is not None else "",
                    f"{extreme:.2f}" if extreme is not None else "",
                ])

        return TypstTable(
            headers=["高度(m)", "风区等级", "最大持续风速Vref(m/s)", "极大极端风速Ve50(m/s)"],
            data=rows,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return []


def _format_value(value: float) -> str:
    if value == 0.0:
        return ""
    return f"{value:.2f}"
