"""IEC standards atom for reporting domain.

LOGIC-PRESERVATION: Ported from assessment entities/iec_standards_atom.py.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import polars as pl
from typing_extensions import override

from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.report_meta import (
    IECStandardsAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.schemas import (
    IECStandardsSchema,
)

IEC_STANDARDS_DATA = pl.DataFrame(
    {
        "iec_class": ["I", "II", "III", "S"],
        "vref": [10.0, 8.5, 7.5, 0.0],
        "ve50": [70.0, 59.5, 52.5, 0.0],
    }
)


@dataclass(frozen=True)
class IECStandardsAtom(ReportAtom[IECStandardsSchema, IECStandardsAtomMeta]):
    """Renders IEC 61400-1 wind class standards table."""

    @property
    @override
    def default_image_caption(self) -> str | None:
        return None

    @property
    @override
    def default_table_caption(self) -> str | None:
        return "IEC 标准风况等级（IEC 61400-1）"

    @override
    def renderTable(self) -> TypstTable | None:
        rows: list[list[str]] = []
        for row in self.df.iter_rows(named=True):
            iec_class = cast(str, row["iec_class"])
            if iec_class == "S":
                vref_str = "-"
                ve50_str = "-"
            else:
                vref_str = f"{row['vref']:.1f}"
                ve50_str = f"{row['ve50']:.1f}"
            rows.append([iec_class, vref_str, ve50_str])

        return TypstTable(
            headers=[
                "IEC 等级",
                "参考风速 Vref (m/s)",
                "五十年一遇极端风速 Ve50 (m/s)",
            ],
            data=rows,
            caption=self.default_table_caption,
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return [
            TypstParagraph(
                text="根据IEC 61400-1标准，不同风况等级对应的参考风速和五十年一遇极端风速如表所示。"
            )
        ]
