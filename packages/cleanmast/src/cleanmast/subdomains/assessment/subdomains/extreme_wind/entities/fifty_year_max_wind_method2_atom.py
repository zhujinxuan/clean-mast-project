"""Fifty-year max wind Method 2 atoms for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path

import polars as pl
from typing_extensions import override

from cleanmast.subdomains.assessment.shared.ir_types import (
    TypstParagraph,
    TypstTable,
)
from cleanmast.subdomains.assessment.shared.protocols.report_atom import ReportAtom
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
    get_height_display_name,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.entities._gumbel_qq import (
    generate_gumbel_qq_subgrid,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.value_objects.schemas import (
    FiftyYearMaxWindResultSchema,
    GumbelParameterSchema,
)


@dataclass
class SingleMastFiftyYearMaxWindMethod2ResultAtom(
    ReportAtom[FiftyYearMaxWindResultSchema, SingleMastMeta]
):
    """Renders fifty-year max wind Method 2 (五日最大法) result table."""

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} 五日最大风速法结果"

    @override
    def renderTable(self) -> TypstTable | None:
        if self.df.is_empty():
            return TypstTable(
                headers=["高度(m)", "风速类型", "五日最大风速法(m/s)", "标准密度风速(m/s)"],
                data=[],
                caption=self.default_table_caption,
            )

        sorted_df = self.df.sort("height")
        rows = []
        for row in sorted_df.iter_rows(named=True):
            height_display = get_height_display_name(row["height"], row["interpolation_marker"] or "")
            wind_type = "持续风速" if row["wind_speed_type"] == "sustained" else "极端风速"
            rows.append([
                height_display,
                wind_type,
                f"{row['max_wind_speed']:.2f}",
                f"{row['standard_density_wind_speed']:.2f}",
            ])

        return TypstTable(
            headers=["高度(m)", "风速类型", "五日最大风速法(m/s)", "标准密度风速(m/s)"],
            data=rows,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        if self.df.is_empty():
            return [TypstParagraph(text=f"{self.meta.mast_name}测风塔暂无有效的五日最大风速法分析数据。")]

        heights_df = self.df.select(["height", "interpolation_marker"]).unique().sort("height")
        height_strs = [
            get_height_display_name(row["height"], row["interpolation_marker"] or "")
            for row in heights_df.iter_rows(named=True)
        ]

        parts = []
        for row in self.df.sort("height").iter_rows(named=True):
            height_display = get_height_display_name(row["height"], row["interpolation_marker"] or "")
            wind_type = "持续风速" if row["wind_speed_type"] == "sustained" else "极端风速"
            parts.append(
                f"{height_display} {wind_type}: {row['max_wind_speed']:.2f}m/s"
                f"(标准密度{row['standard_density_wind_speed']:.2f}m/s)"
            )

        text = (
            f"{self.meta.mast_name}测风塔五十年一遇最大风速估算(方法二:五日最大法)。"
            f"分析高度包括{', '.join(height_strs)}。"
            f"各高度结果如下：{'；'.join(parts)}。"
        )
        return [TypstParagraph(text=text)]


@dataclass
class SingleMastFiftyYearMaxWindMethod2ParamsAtom(
    ReportAtom[GumbelParameterSchema, SingleMastMeta]
):
    """Renders Gumbel parameter table for Method 2."""

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} Gumbel分布拟合参数"

    @override
    def renderTable(self) -> TypstTable | None:
        if self.df.is_empty():
            return TypstTable(
                headers=["高度(m)", "风速类型", "μ", "β", "样本数量", "样本均值(m/s)", "样本标准差(m/s)"],
                data=[],
                caption=self.default_table_caption,
            )

        sorted_df = self.df.sort("height")
        rows = []
        for row in sorted_df.iter_rows(named=True):
            height_display = get_height_display_name(row["height"], "")
            wind_type = "持续风速" if row["wind_speed_type"] == "sustained" else "极端风速"
            rows.append([
                height_display,
                wind_type,
                f"{row['mu']:.3f}",
                f"{row['beta']:.3f}",
                str(row["sample_count"]),
                f"{row['sample_mean']:.2f}",
                f"{row['sample_std']:.2f}",
            ])

        return TypstTable(
            headers=["高度(m)", "风速类型", "μ", "β", "样本数量", "样本均值(m/s)", "样本标准差(m/s)"],
            data=rows,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return []


@dataclass
class SingleMastFiftyYearMaxWindMethod2QQSustainedAtom(
    ReportAtom[GumbelParameterSchema, SingleMastMeta]
):
    """Renders Gumbel Q-Q plot for sustained wind speeds."""

    @property
    @override
    def default_image_caption(self) -> str | None:
        return f"{self.meta.mast_name} 持续风速Gumbel Q-Q图"

    @property
    @override
    def default_table_caption(self) -> str | None:
        return None

    @override
    def renderTable(self) -> TypstTable | None:
        return None

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        if self.df.is_empty():
            return Path()

        data_df = self.df.filter(pl.col("wind_speed_type") == "sustained")
        data_list = []
        for row in data_df.iter_rows(named=True):
            data_list.append({
                "height": row["height"],
                "wind_data": row["sample_data"] or [],
                "mu": row["mu"],
                "beta": row["beta"],
            })

        if not data_list:
            return Path()

        return generate_gumbel_qq_subgrid(
            data_list=data_list,
            mast_name=self.meta.mast_name,
            output_dir=output_dir,
            wind_speed_type="sustained",
        )

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return []


@dataclass
class SingleMastFiftyYearMaxWindMethod2QQExtremeAtom(
    ReportAtom[GumbelParameterSchema, SingleMastMeta]
):
    """Renders Gumbel Q-Q plot for extreme wind speeds."""

    @property
    @override
    def default_image_caption(self) -> str | None:
        return f"{self.meta.mast_name} 极端风速Gumbel Q-Q图"

    @property
    @override
    def default_table_caption(self) -> str | None:
        return None

    @override
    def renderTable(self) -> TypstTable | None:
        return None

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        if self.df.is_empty():
            return Path()

        data_df = self.df.filter(pl.col("wind_speed_type") == "extreme")
        data_list = []
        for row in data_df.iter_rows(named=True):
            data_list.append({
                "height": row["height"],
                "wind_data": row["sample_data"] or [],
                "mu": row["mu"],
                "beta": row["beta"],
            })

        if not data_list:
            return Path()

        return generate_gumbel_qq_subgrid(
            data_list=data_list,
            mast_name=self.meta.mast_name,
            output_dir=output_dir,
            wind_speed_type="extreme",
        )

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return []
