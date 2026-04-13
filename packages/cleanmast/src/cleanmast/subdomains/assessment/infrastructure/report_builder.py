"""AssessmentReportBuilder for orchestrating report generation.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service Layer ✓ | Report Pattern ✓
"""

from __future__ import annotations

from pathlib import Path
from typing import Self, TypedDict

from typst_ir import (
    compile_typst_to_docx,
    compile_typst_to_pdf,
    serialize,
)

from cleanmast.subdomains.assessment.domain.protocols.section import Section
from cleanmast.subdomains.assessment.domain.types import (
    TypstDocument,
    TypstSection,
)


class BuildResult(TypedDict, total=False):
    """Result dictionary from AssessmentReportBuilder.build().
    
    Keys:
        typ: Path to the generated Typst source file (always present)
        pdf: Path to the generated PDF file (if compile_pdf=True and succeeds)
        docx: Path to the generated DOCX file (if compile_docx=True and succeeds)
        docx_warning: Error message string (if compile_docx=True but fails)
    """
    typ: Path
    pdf: Path
    docx: Path
    docx_warning: str


class AssessmentReportBuilder:
    """Builds reports from atoms using IR-based rendering.

    Orchestrates the generation of Typst documents by collecting sections
    of ReportAtoms and rendering them into a complete report with images,
    tables, and summaries.

    Example:
        >>> builder = AssessmentReportBuilder("Monthly Wind Report", Path("output/"))
        >>> builder.add_section(wind_section)
        >>> results = builder.build()
    """

    def __init__(self, title: str, output_dir: Path) -> None:
        """Initialize the report builder.

        Args:
            title: The report title (used in document header)
            output_dir: Directory where report.typ and images/ will be created
        """
        self.title = title
        self.output_dir = output_dir
        self._sections: list[Section] = []

    def add_section(self, section: Section) -> Self:
        """Add any Section implementation.

        Args:
            section: Section instance (WindRoseSection, TurbulenceSubsection, etc.)

        Returns:
            Self for method chaining
        """
        self._sections.append(section)
        return self

    def build(self, compile_pdf: bool = True, compile_docx: bool = True) -> BuildResult:
        """Generate complete Typst document using IR-based rendering.

        Creates the output directory structure, generates images for all atoms,
        and assembles a complete Typst document from IR nodes.

        Args:
            compile_pdf: Whether to compile the report to PDF (default: True)
            compile_docx: Whether to compile the report to DOCX (default: True)

        Returns:
            Dictionary containing paths to generated files. Always includes 'typ'.
            May include 'pdf', 'docx', or 'docx_warning' depending on compilation.
        """
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = self.output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # Build Typst IR document
        all_children: list[TypstSection] = [section.render_ir(images_dir) for section in self._sections]

        doc = TypstDocument(children=all_children)
        json_str = doc.model_dump_json()

        # Serialize to Typst markup
        typst_markup = serialize(doc)

        preamble = '''// Chinese text support
#set text(font: ("Linux Libertine", "Source Han Serif SC"))
#set heading(numbering: "1.")

'''
        full_markup = preamble + typst_markup

        # Write document to file
        report_path = self.output_dir / "report.typ"
        report_path.write_text(full_markup, encoding='utf-8')

        results: BuildResult = {"typ": report_path}

        # PDF compilation
        if compile_pdf:
            try:
                results["pdf"] = compile_typst_to_pdf(report_path, self.output_dir, json_content=json_str)
            except RuntimeError as e:
                raise RuntimeError(
                    f"PDF generation failed: {e}\n"
                    f"Typst file created at: {report_path}"
                ) from e

        # DOCX compilation
        if compile_docx:
            try:
                results["docx"] = compile_typst_to_docx(report_path, self.output_dir, json_content=json_str)
            except (ImportError, RuntimeError) as e:
                results["docx_warning"] = str(e)

        return results

    def build_typst(self) -> TypstDocument:
        """Build Typst IR document without compilation.

        Constructs a TypstDocument from all sections using their
        render_ir() methods. Images are generated as side effects.

        Returns:
            TypstDocument containing all section IR nodes
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = self.output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        all_children: list[TypstSection] = [section.render_ir(images_dir) for section in self._sections]

        return TypstDocument(children=all_children)
