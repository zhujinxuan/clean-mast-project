"""ReportBuilder protocol for orchestrating report generation."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, Self, TypedDict

from typst_ir import TypstDocument

from cleanmast.subdomains.reporting.protocols.section import Section


class BuildResult(TypedDict, total=False):
    """Result dictionary from ReportBuilder.build().

    Keys:
        typ: Path to the generated Typst source file (always present)
        pdf: Path to the generated PDF file (always present)
        docx: Path to the generated DOCX file (always present)
    """

    typ: Path
    pdf: Path
    docx: Path


class ReportBuilder(Protocol):
    """Builds reports from atoms using IR-based rendering.

    Orchestrates the generation of Typst documents by collecting sections
    of ReportAtoms and rendering them into a complete report with images,
    tables, and summaries.

    Example:
        >>> builder: ReportBuilder = AssessmentReportBuilder("Monthly Wind Report", Path("output/"))
        >>> builder.add_section(wind_section)
        >>> results = builder.build()
    """

    def add_section(self, section: Section) -> Self:
        """Add any Section implementation.

        Args:
            section: Section instance (WindRoseSection, TurbulenceSubsection, etc.)

        Returns:
            Self for method chaining
        """
        ...

    def build(self) -> BuildResult:
        """Generate complete report and return paths to generated files.

        Returns:
            Dictionary containing paths to generated files. Always includes 'typ', 'pdf', and 'docx'.
        """
        ...

    def build_typst(self) -> TypstDocument:
        """Build Typst IR document without compilation.

        Constructs a TypstDocument from all sections using their
        render_ir() methods. Images are generated as side effects.

        Returns:
            TypstDocument containing all section IR nodes
        """
        ...
