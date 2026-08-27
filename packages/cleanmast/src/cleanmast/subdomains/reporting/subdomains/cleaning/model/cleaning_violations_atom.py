"""Cleaning violations table atom for 2.3.3 (缺测与不合理数据处理)."""

from pathlib import Path
from typing import cast

from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.cleaning.model.constants import (
    translate_rule_name,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model.report_meta import (
    CleaningViolationsAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model.schemas import (
    CleaningViolationsSchema,
)


class CleaningViolationsAtom(
    ReportAtom[CleaningViolationsSchema, CleaningViolationsAtomMeta]
):
    """Renders per-rule removal counts as the 2.3.3 violations table.

    Summary: one sentence per mast (removal total, violation percentage
    when the stats file provides it, or a missing-file note). Table: one
    row per mast × column × rule (测风塔 / 数据列 / 剔除规则 / 剔除点数).
    Image: none.
    """

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return "各测风塔分规则剔除点数统计"

    @override
    def renderTable(self) -> TypstTable | None:
        if self.df.is_empty():
            return None
        data: list[list[str]] = []
        for row in self.df.iter_rows(named=True):
            data.append([
                cast(str, row["mast_name"]),
                cast(str, row["column_name"]),
                translate_rule_name(cast(str, row["rule_name"])),
                str(cast(int, row["violation_count"])),
            ])
        return TypstTable(
            headers=["测风塔", "数据列", "剔除规则", "剔除点数"],
            data=data,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        lines = [line for line in self.meta.summary_lines if line]
        if not lines:
            return []
        return [TypstParagraph(text="".join(lines))]
