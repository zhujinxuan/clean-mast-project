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
    """Renders one mast's per-rule removal counts as a 2.3.3 table.

    Table: one row per column × rule, pre-sorted by assemble (sensor type
    风速 → 风向 → 温度 → 气压 → 其他, then height ascending, then rule
    name); the 数据列 cell shows the Chinese sensor label from
    ``meta.column_labels``, falling back to the raw column name when no
    sensor metadata matched. Caption: ``{mast} 分规则剔除点数统计``.
    Summary: the missing-stats note (``meta.note``) only — no table in
    that case. Image: none.
    """

    @property
    @override
    def default_table_caption(self) -> str | None:
        return f"{self.meta.mast_name} 分规则剔除点数统计"

    @override
    def renderTable(self) -> TypstTable | None:
        if self.df.is_empty():
            return None
        data: list[list[str]] = []
        for row in self.df.iter_rows(named=True):
            column = cast(str, row["column_name"])
            data.append([
                self.meta.column_labels.get(column, column),
                translate_rule_name(cast(str, row["rule_name"])),
                str(cast(int, row["violation_count"])),
            ])
        return TypstTable(
            headers=["数据列", "剔除规则", "剔除点数"],
            data=data,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        if not self.meta.note:
            return []
        return [TypstParagraph(text=self.meta.note)]
