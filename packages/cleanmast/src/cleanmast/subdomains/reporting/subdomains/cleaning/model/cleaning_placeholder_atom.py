"""Wave 1 placeholder atom for the cleaning subsections."""

from pathlib import Path

from typing_extensions import override
from typst_ir import TypstParagraph, TypstTable

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.cleaning.model.report_meta import (
    CleaningAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model.schemas import (
    CleaningPlaceholderSchema,
)


class CleaningPlaceholderAtom(
    ReportAtom[CleaningPlaceholderSchema, CleaningAtomMeta]
):
    """Renders one line of placeholder text.

    Summary: the placeholder line. Table: none. Image: none. Wave 2 swaps
    this atom for the real per-subsection atoms (coverage tables, violation
    statistics, regression figures).
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
        return [TypstParagraph(text=self.meta.text)]
