"""Site-level cross-mast conclusion atoms for reporting domain.

Renders the 2.6.5 site determination table and conclusion paragraph built
from the cross-mast pass over per-mast comparison results.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.report_meta import (
    SiteLevelAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.schemas import (
    SiteConclusionSchema,
    SiteDeterminationSchema,
)


@dataclass(frozen=True)
class SiteDeterminationAtom(
    ReportAtom[SiteDeterminationSchema, SiteLevelAtomMeta]
):
    """Renders the site-level cross-mast determination table."""

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return "场址五十年一遇风速判定"

    @override
    def renderTable(self) -> TypstTable | None:
        if self.df.is_empty():
            return TypstTable(
                headers=[
                    "高度(m)",
                    "跨塔最大保守持续(m/s)",
                    "跨塔最大保守极大(m/s)",
                    "判定等级",
                ],
                data=[],
                caption=self.default_table_caption,
            )

        rows = []
        for row in self.df.sort("height").iter_rows(named=True):
            rows.append([
                f"{cast(float, row['height']):.1f}",
                f"{cast(float, row['cross_mast_max_sustained']):.2f}",
                f"{cast(float, row['cross_mast_max_extreme']):.2f}",
                f"{cast(str, row['wind_class'])}类",
            ])

        return TypstTable(
            headers=[
                "高度(m)",
                "跨塔最大保守持续(m/s)",
                "跨塔最大保守极大(m/s)",
                "判定等级",
            ],
            data=rows,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return []


@dataclass(frozen=True)
class SiteConclusionAtom(ReportAtom[SiteConclusionSchema, SiteLevelAtomMeta]):
    """Renders the site-level conclusion paragraph (one row = one sentence)."""

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return None

    @override
    def renderTable(self) -> TypstTable | None:
        return None

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return [
            TypstParagraph(text=cast(str, row["text"]))
            for row in self.df.iter_rows(named=True)
        ]
