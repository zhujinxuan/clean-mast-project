"""Fifty-year max wind summary atoms for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass, field
from pathlib import Path

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
    FiftyYearMaxWindComparisonSchema,
    IECWindClassSchema,
)


@dataclass
class _ComparisonAtomMixin(ReportAtom[FiftyYearMaxWindComparisonSchema, SingleMastMeta]):
    _height_markers: dict[float, str] = field(default_factory=dict, init=False, repr=False)

    @classmethod
    def create(cls, schema, df, meta):
        instance = super().create(schema, df, meta)
        markers = {}
        for row in df.iter_rows(named=True):
            markers[row["height"]] = row.get("interpolation_marker") or ""
        instance._height_markers = markers
        return instance

    def _get_marker(self, height: float) -> str:
        return getattr(self, "_height_markers", {}).get(height, "")


@dataclass
class SingleMastFiftyYearMaxWindComparisonSustainedAtom(_ComparisonAtomMixin):
    """Renders fifty-year max wind sustained comparison across methods."""

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} 50年一遇持续风速多方法对比"

    @override
    def renderTable(self) -> TypstTable | None:
        if self.df.is_empty():
            return TypstTable(
                headers=["高度(m)", "5倍平均风速法(m/s)", "五日最大风速法(m/s)", "极端风速模型法(m/s)", "保守估计(m/s)"],
                data=[],
                caption=self._resolve_table_caption(),
            )

        sorted_df = self.df.sort("height")
        rows = []
        for row in sorted_df.iter_rows(named=True):
            height_display = get_height_display_name(row["height"], self._get_marker(row["height"]))
            rows.append([
                height_display,
                self._format_value(row["method1"]),
                self._format_value(row["method2"]),
                self._format_value(row["method3"]),
                self._format_value(row["conservative_max"]),
            ])

        return TypstTable(
            headers=["高度(m)", "5倍平均风速法(m/s)", "五日最大风速法(m/s)", "极端风速模型法(m/s)", "保守估计(m/s)"],
            data=rows,
            caption=self._resolve_table_caption(),
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        if self.df.is_empty():
            return [TypstParagraph(text=f"{self.meta.mast_name}测风塔暂无有效的50年一遇持续风速对比数据。")]

        sorted_df = self.df.sort("height")
        height_parts = []
        for row in sorted_df.iter_rows(named=True):
            height_display = get_height_display_name(row["height"], self._get_marker(row["height"]))
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

    def _format_value(self, value: float) -> str:
        if value == 0.0:
            return ""
        return f"{value:.2f}"


@dataclass
class SingleMastFiftyYearMaxWindComparisonExtremeAtom(_ComparisonAtomMixin):
    """Renders fifty-year max wind extreme comparison across methods."""

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} 50年一遇极端风速多方法对比"

    @override
    def renderTable(self) -> TypstTable | None:
        if self.df.is_empty():
            return TypstTable(
                headers=["高度(m)", "5倍平均风速法(m/s)", "五日最大风速法(m/s)", "极端风速模型法(m/s)", "保守估计(m/s)"],
                data=[],
                caption=self._resolve_table_caption(),
            )

        sorted_df = self.df.sort("height")
        rows = []
        for row in sorted_df.iter_rows(named=True):
            height_display = get_height_display_name(row["height"], self._get_marker(row["height"]))
            rows.append([
                height_display,
                self._format_value(row["method1"]),
                self._format_value(row["method2"]),
                self._format_value(row["method3"]),
                self._format_value(row["conservative_max"]),
            ])

        return TypstTable(
            headers=["高度(m)", "5倍平均风速法(m/s)", "五日最大风速法(m/s)", "极端风速模型法(m/s)", "保守估计(m/s)"],
            data=rows,
            caption=self._resolve_table_caption(),
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        if self.df.is_empty():
            return [TypstParagraph(text=f"{self.meta.mast_name}测风塔暂无有效的50年一遇极端风速对比数据。")]

        sorted_df = self.df.sort("height")
        height_parts = []
        for row in sorted_df.iter_rows(named=True):
            height_display = get_height_display_name(row["height"], self._get_marker(row["height"]))
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

    def _format_value(self, value: float) -> str:
        if value == 0.0:
            return ""
        return f"{value:.2f}"


@dataclass
class SingleMastIECWindClassAtom(
    ReportAtom[IECWindClassSchema, SingleMastMeta]
):
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
                caption=self._resolve_table_caption(),
            )

        rows = []
        for row in self.df.iter_rows(named=True):
            wind_class = row["wind_class"]
            height = row.get("height")

            if height is None:
                # Reference rows
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
                # Per-height classification rows
                sustained = row.get("conservative_sustained")
                extreme = row.get("conservative_extreme")
                rows.append([
                    f"{height:.1f}",
                    f"{wind_class}类",
                    f"{sustained:.2f}" if sustained is not None else "",
                    f"{extreme:.2f}" if extreme is not None else "",
                ])

        return TypstTable(
            headers=["高度(m)", "风区等级", "最大持续风速Vref(m/s)", "极大极端风速Ve50(m/s)"],
            data=rows,
            caption=self._resolve_table_caption(),
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return []
