"""IEC standards atom for no-mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-002-entities-value-objects
Compliance: Subdomain layout ✓ | Entity ✓ | Atom Pattern ✓
"""

from dataclasses import dataclass
from pathlib import Path

import polars as pl
from typing_extensions import override

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.types import (
    TypstParagraph,
    TypstTable,
)
from cleanmast.subdomains.assessment.domain.value_objects.no_masts.report_meta import (
    NoMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.no_masts.schemas import (
    IECStandardsSchema,
)

IEC_STANDARDS_DATA = pl.DataFrame(
    {
        "iec_class": ["I", "II", "III", "S"],
        "vref": [10.0, 8.5, 7.5, 0.0],
        "ve50": [70.0, 59.5, 52.5, 0.0],
    }
)


@dataclass
class NoMastIECStandardsAtom(ReportAtom[IECStandardsSchema, NoMastMeta]):
    """Renders IEC 61400-1 wind class standards table.

    - Table: IEC class, Vref, Ve50
    - Image: No image for standards table (returns empty Path)
    - Summary: Chinese description of IEC standards
    """

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
        """Render as Typst table with IEC 61400-1 wind classes."""
        rows: list[list[str]] = []
        for row in self.df.iter_rows(named=True):
            iec_class = row["iec_class"]
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
            caption=self._resolve_table_caption(),
        )

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        """No image generation for IEC standards table.

        Returns a placeholder Path.
        """
        return Path()

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        """Generate Chinese summary of IEC 61400-1 wind class standards."""
        return [
            TypstParagraph(
                text="根据IEC 61400-1标准，不同风况等级对应的参考风速和五十年一遇极端风速如表所示。"
            )
        ]
