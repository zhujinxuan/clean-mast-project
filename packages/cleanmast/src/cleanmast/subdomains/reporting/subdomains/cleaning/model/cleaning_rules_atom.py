"""Cleaning-rules table atom for 2.3.3 (缺测与不合理数据处理)."""

from pathlib import Path
from typing import cast

from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.cleaning.model.constants import (
    CLEANING_RULES_INTRO,
    translate_rule_name,
    translate_sensor_type,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model.report_meta import (
    CleaningRulesAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model.schemas import (
    CleaningRulesSchema,
)


def format_height_filter(height_min: float | None, height_max: float | None) -> str:
    """Human-readable 适用高度 cell from the rule height-filter bounds."""
    if height_min is None and height_max is None:
        return "全部高度"
    if height_max is None:
        return f"≥{height_min:g}m"
    if height_min is None:
        return f"≤{height_max:g}m"
    return f"[{height_min:g}, {height_max:g}]m"


class CleaningRulesAtom(ReportAtom[CleaningRulesSchema, CleaningRulesAtomMeta]):
    """Renders the enabled cleaning rules as the 2.3.3 rules table.

    Summary: the GB/T 37523-2019 intro sentence. Table: one row per rule
    (规则名称 / 传感器类型 / 适用高度(m) / 判定条件). Image: none.
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return "测风数据清洗规则"

    @override
    def renderTable(self) -> TypstTable | None:
        if self.df.is_empty():
            return None
        data: list[list[str]] = []
        for row in self.df.iter_rows(named=True):
            data.append([
                translate_rule_name(cast(str, row["rule_name"])),
                translate_sensor_type(cast(str, row["sensor_type"])),
                format_height_filter(
                    cast("float | None", row["height_min"]),
                    cast("float | None", row["height_max"]),
                ),
                cast(str, row["condition"]),
            ])
        return TypstTable(
            headers=["规则名称", "传感器类型", "适用高度(m)", "判定条件"],
            data=data,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return [TypstParagraph(text=CLEANING_RULES_INTRO)]
