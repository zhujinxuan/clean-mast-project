"""AssessmentReportBuilder for orchestrating report generation.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service Layer ✓ | Report Pattern ✓
"""

from __future__ import annotations

from pathlib import Path
from typing import Self, TypedDict

from cleanmast.subdomains.assessment.domain.protocols.section import Section
from cleanmast.subdomains.assessment.domain.types import (
    TypstChild,
    TypstDocument,
    TypstHeading,
)
from cleanmast.subdomains.assessment.infrastructure.compiler import (
    compile_typst_to_docx,
    compile_typst_to_pdf,
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
    """Builds reports from atoms.

    Orchestrates the generation of Typst documents by collecting sections
    of ReportAtoms and rendering them into a complete report with images,
    tables, and summaries.

    Example:
        >>> builder = AssessmentReportBuilder("Monthly Wind Report", Path("output/"))
        >>> builder.add_section("Wind Analysis", [atom1, atom2])
        >>> report_path = builder.build()
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
            section: Section instance (TemplatedSection, WindRoseSection, etc.)

        Returns:
            Self for method chaining
        """
        self._sections.append(section)
        return self

    def build(self, compile_pdf: bool = True, compile_docx: bool = True) -> BuildResult:
        """Generate complete Typst document.

        Creates the output directory structure, generates images for all atoms,
        and assembles a complete Typst document with sections, figures, tables,
        and summaries.

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

        # Build Typst document content
        lines: list[str] = []

        # Preamble with Chinese font support
        lines.append('// Chinese text support')
        lines.append('#set text(font: ("Linux Libertine", "Source Han Serif SC"))')
        lines.append('#set heading(numbering: "1.")')
        lines.append('')

        # Report title
        lines.append(f'= {self.title}')
        lines.append('')

        # Process each section
        for section in self._sections:
            content = section.render(images_dir)
            lines.append(content)
            lines.append('')  # Extra blank line between sections

        # Write document to file
        report_path = self.output_dir / "report.typ"
        report_path.write_text('\n'.join(lines), encoding='utf-8')

        results: BuildResult = {"typ": report_path}

        # PDF is required
        if compile_pdf:
            try:
                results["pdf"] = compile_typst_to_pdf(report_path, self.output_dir)
            except RuntimeError as e:
                raise RuntimeError(
                    f"PDF generation failed: {e}\n"
                    f"Typst file created at: {report_path}"
                ) from e

        # DOCX is optional
        if compile_docx:
            try:
                results["docx"] = compile_typst_to_docx(report_path, self.output_dir)
            except (ImportError, RuntimeError) as e:
                results["docx_warning"] = str(e)

        return results

    def build_typst(
        self,
        compile_pdf: bool = True,
        compile_docx: bool = True
    ) -> TypstDocument:
        """Build Typst IR document.

        Constructs a TypstDocument from all sections using their
        render_ir() methods. Images are generated as side effects.

        Args:
            compile_pdf: Whether to compile PDF (for compatibility, not used in IR path)
            compile_docx: Whether to compile DOCX (for compatibility, not used in IR path)

        Returns:
            TypstDocument containing all section IR nodes
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = self.output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        all_children: list[TypstChild] = [TypstHeading(text=self.title, level=1)]

        for section in self._sections:
            section_nodes = section.render_ir(images_dir)
            adjusted_nodes = self._adjust_heading_levels(section_nodes, base_level=2)
            all_children.extend(adjusted_nodes)

        return TypstDocument(children=all_children)

    def _adjust_heading_levels(
        self, nodes: list[TypstChild], base_level: int
    ) -> list[TypstChild]:
        adjusted: list[TypstChild] = []
        for node in nodes:
            if isinstance(node, TypstHeading):
                new_level = max(base_level, node.level + 1)
                adjusted.append(TypstHeading(text=node.text, level=new_level))
            else:
                adjusted.append(node)
        return adjusted
