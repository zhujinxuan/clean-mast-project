"""Method-text atom for 2.3.4 塔影效应处理."""

from pathlib import Path

from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.cleaning.model.report_meta import (
    TowerShadingMethodAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model.schemas import (
    TowerShadingMethodSchema,
)

#: Constant method sentence (the max-merge formula renders as a TypstEquation
#: in the section body — same convention as the air-density section).
TOWER_SHADING_METHOD_TEXT = (
    "对同一高度设有两个风速传感器的通道，"
    "依据《风电场工程风能资源测量与评估技术规范》（NB/T 31147-2018）"
    "进行塔影修正，逐时刻取两通道较大值，"
    "修正前后分扇区风速对比见下表。"
)

#: Variant for projects where every mast is single-channel at every height
#: (verified over the full WS-avg sensor list, not only cleaning heights):
#: the method is stated for completeness and the verification outcome
#: replaces the comparison-table reference — no channel was corrected.
TOWER_SHADING_METHOD_TEXT_NO_TABLE = (
    "对同一高度设有两个风速传感器的通道，"
    "依据《风电场工程风能资源测量与评估技术规范》（NB/T 31147-2018）"
    "进行塔影修正，逐时刻取两通道较大值。"
    "经检验，各测风塔各高度层均为单通道风速传感器，不涉及塔影修正。"
)


class TowerShadingMethodAtom(
    ReportAtom[TowerShadingMethodSchema, TowerShadingMethodAtomMeta]
):
    """Renders the 2.3.4 method paragraph.

    Summary: the constant method sentence (standard citation + max rule).
    Table: none. Image: none. The formula itself is a display TypstEquation
    inserted by ``TowerShadingSection.render_ir`` after the summaries.
    """

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
        return [TypstParagraph(text=self.df["text"][0])]
