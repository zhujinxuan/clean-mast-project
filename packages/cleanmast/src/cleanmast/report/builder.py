"""ReportBuilder for orchestrating report generation."""

from __future__ import annotations

from pathlib import Path
from typing import Self

from .protocols import Section
from .compiler import compile_typst_to_pdf


class ReportBuilder:
    """Builds reports from atoms.

    Orchestrates the generation of Typst documents by collecting sections
    of ReportAtoms and rendering them into a complete report with images,
    tables, and summaries.

    Example:
        >>> builder = ReportBuilder("Monthly Wind Report", Path("output/"))
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

    def build(self, compile_pdf: bool = True) -> dict[str, Path | str]:
        """Generate complete Typst document.

        Creates the output directory structure, generates images for all atoms,
        and assembles a complete Typst document with sections, figures, tables,
        and summaries.

        Args:
            compile_pdf: Whether to compile the report to PDF (default: True)

        Returns:
            Dictionary containing paths to generated files. Always includes 'typ'.
            May include 'pdf' depending on compilation.
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

        results: dict[str, Path | str] = {"typ": report_path}

        # PDF is required
        if compile_pdf:
            try:
                results["pdf"] = compile_typst_to_pdf(report_path, self.output_dir)
            except RuntimeError as e:
                raise RuntimeError(
                    f"PDF generation failed: {e}\n"
                    f"Typst file created at: {report_path}"
                ) from e

        return results
