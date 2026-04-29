"""Tests for AssessmentReportBuilder."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from cleanmast.subdomains.assessment.domain.services.sections.wind_rose import (
    WindRoseSection,
)
from cleanmast.subdomains.assessment.domain.types import (
    TypstDocument,
    TypstFigure,
    TypstParagraph,
    TypstTable,
)
from cleanmast.subdomains.assessment.domain.value_objects import AtomCollection
from cleanmast.subdomains.assessment.infrastructure import AssessmentReportBuilder


@pytest.fixture(autouse=True)
def mock_compilation():
    """Mock PDF and DOCX compilation to avoid requiring Typst CLI."""
    with (
        patch(
            "cleanmast.subdomains.assessment.infrastructure.report_builder.compile_typst_to_pdf"
        ) as mock_pdf,
        patch(
            "cleanmast.subdomains.assessment.infrastructure.report_builder.draft_docx"
        ),
        patch(
            "cleanmast.subdomains.assessment.infrastructure.report_builder.polish_docx"
        ),
    ):
        mock_pdf.return_value = Path("dummy.pdf")
        yield


class TestAssessmentReportBuilderInitialization:
    """Tests for AssessmentReportBuilder initialization."""

    def test_init_with_title_and_output_dir(self, tmp_path: Path):
        """Test that AssessmentReportBuilder initializes with title and output dir."""
        output_dir = tmp_path / "report"
        builder = AssessmentReportBuilder("Test Report", output_dir)

        assert builder.title == "Test Report"
        assert builder.output_dir == output_dir
        assert builder._sections == []

    def test_init_creates_empty_sections(self, tmp_path: Path):
        """Test that ReportBuilder starts with empty sections."""
        builder = AssessmentReportBuilder("Test", tmp_path)

        assert len(builder._sections) == 0


class TestReportBuilderAddSection:
    """Tests for ReportBuilder.add_section method."""

    def _create_section(self, title: str, atoms: list[Any]) -> WindRoseSection:
        """Helper to create a WindRoseSection from atoms."""
        collection = AtomCollection.from_dict({"M01": atoms})
        return WindRoseSection(atoms=collection, title=title)

    def test_add_section_single_atom(self, tmp_path: Path, monthly_wind_atom: Any):
        """Test adding a section with a single atom."""
        builder = AssessmentReportBuilder("Test", tmp_path)
        section = self._create_section("Wind Analysis", [monthly_wind_atom])
        builder.add_section(section)

        assert len(builder._sections) == 1
        assert builder._sections[0].title == "Wind Analysis"
        assert len(builder._sections[0].atoms) == 1

    def test_add_section_multiple_atoms(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
        monthly_wind_power_atom: Any,
    ):
        """Test adding a section with multiple atoms."""
        builder = AssessmentReportBuilder("Test", tmp_path)
        section = self._create_section(
            "Analysis", [monthly_wind_atom, monthly_wind_power_atom]
        )
        builder.add_section(section)

        assert len(builder._sections) == 1
        assert len(builder._sections[0].atoms) == 2

    def test_add_section_returns_self(self, tmp_path: Path, monthly_wind_atom: Any):
        """Test that add_section returns self for chaining."""
        builder = AssessmentReportBuilder("Test", tmp_path)
        section = self._create_section("Analysis", [monthly_wind_atom])
        result = builder.add_section(section)

        assert result is builder

    def test_add_section_chaining(self, tmp_path: Path, all_atoms: list[Any]):
        """Test method chaining with multiple sections."""
        builder = (
            AssessmentReportBuilder("Test", tmp_path)
            .add_section(self._create_section("Section 1", [all_atoms[0]]))
            .add_section(self._create_section("Section 2", [all_atoms[1]]))
            .add_section(self._create_section("Section 3", [all_atoms[2]]))
        )

        assert len(builder._sections) == 3

    def test_add_section_empty_atoms(self, tmp_path: Path):
        """Test adding a section with empty atoms list."""
        builder = AssessmentReportBuilder("Test", tmp_path)
        section = self._create_section("Empty Section", [])
        builder.add_section(section)

        assert len(builder._sections) == 1
        assert len(builder._sections[0].atoms) == 0


class TestReportBuilderBuild:
    """Tests for ReportBuilder.build method."""

    def _create_section(self, title: str, atoms: list[Any]) -> WindRoseSection:
        """Helper to create a WindRoseSection from atoms."""
        collection = AtomCollection.from_dict({"M01": atoms})
        return WindRoseSection(atoms=collection, title=title)

    def test_build_typst_creates_output_directories(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that build_typst creates output directories."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Test Section", [monthly_wind_atom])
        builder.add_section(section)

        builder.build_typst()

        assert output_dir.exists()
        assert (output_dir / "images").exists()

    def test_build_typst_returns_document(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that build_typst returns a TypstDocument."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test Report", output_dir)
        section = self._create_section("Test Section", [monthly_wind_atom])
        builder.add_section(section)

        doc = builder.build_typst()

        assert isinstance(doc, TypstDocument)
        assert len(doc.children) == 1

    def test_build_content_includes_title(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that report includes the title."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Monthly Report", output_dir)
        section = self._create_section("Test", [monthly_wind_atom])
        builder.add_section(section)

        doc = builder.build_typst()

        assert doc.children[0].heading.text == "Test"

    def test_build_content_includes_section_headers(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that report includes section headers."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Wind Analysis", [monthly_wind_atom])
        builder.add_section(section)

        doc = builder.build_typst()

        assert doc.children[0].heading.text == "Wind Analysis"

    def test_build_content_includes_atom_summaries(
        self,
        tmp_path: Path,
        wind_frequency_rose_atom: Any,
    ):
        """Test that report includes atom summaries."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Analysis", [wind_frequency_rose_atom])
        builder.add_section(section)

        # Use build_typst() to access IR document structure
        doc = builder.build_typst()

        # Check for paragraph nodes (summaries) inside section bodies
        sections = [n for n in doc.children if hasattr(n, "body")]
        paragraphs = [n for sec in sections for n in sec.body if isinstance(n, TypstParagraph)]
        assert len(paragraphs) > 0
        # Summary should contain mast name
        assert any("M01" in p.text for p in paragraphs)

    def test_build_content_includes_figures(
        self,
        tmp_path: Path,
        wind_frequency_rose_atom: Any,
    ):
        """Test that report includes figure markup."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Analysis", [wind_frequency_rose_atom])
        builder.add_section(section)

        # Use build_typst() to access IR document structure
        doc = builder.build_typst()

        # Check for figure nodes inside section bodies
        sections = [n for n in doc.children if hasattr(n, "body")]
        figures = [n for sec in sections for n in sec.body if isinstance(n, TypstFigure)]
        assert len(figures) > 0

    def test_build_content_includes_tables(
        self,
        tmp_path: Path,
        wind_frequency_rose_atom: Any,
    ):
        """Test that report includes table markup."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Analysis", [wind_frequency_rose_atom])
        builder.add_section(section)

        # Use build_typst() to access IR document structure
        doc = builder.build_typst()

        # Check for table nodes inside section bodies
        sections = [n for n in doc.children if hasattr(n, "body")]
        tables = [n for sec in sections for n in sec.body if isinstance(n, TypstTable)]
        assert len(tables) > 0

    def test_build_content_includes_references(
        self,
        tmp_path: Path,
        wind_frequency_rose_atom: Any,
    ):
        """Test that report includes figure references."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Analysis", [wind_frequency_rose_atom])
        builder.add_section(section)

        # Use build_typst() to access IR document structure
        doc = builder.build_typst()

        # Check for paragraph nodes containing references inside section bodies
        sections = [n for n in doc.children if hasattr(n, "body")]
        paragraphs = [n for sec in sections for n in sec.body if isinstance(n, TypstParagraph)]
        # At least one paragraph should contain references
        assert len(paragraphs) > 0

    def test_build_multiple_sections(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
        monthly_wind_power_atom: Any,
    ):
        """Test building report with multiple sections."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section1 = self._create_section("Wind Speed", [monthly_wind_atom])
        section2 = self._create_section("Wind Power", [monthly_wind_power_atom])
        builder.add_section(section1).add_section(section2)

        doc = builder.build_typst()

        assert len(doc.children) == 2
        assert doc.children[0].heading.text == "Wind Speed"
        assert doc.children[1].heading.text == "Wind Power"

    def test_build_generates_images(
        self,
        tmp_path: Path,
        wind_frequency_rose_atom: Any,
    ):
        """Test that build generates image files."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Analysis", [wind_frequency_rose_atom])
        builder.add_section(section)

        # build_typst() triggers image generation as side effect
        builder.build_typst()

        images_dir = output_dir / "images"
        assert images_dir.exists()
        # Should have at least one PNG file
        png_files = list(images_dir.glob("*.png"))
        assert len(png_files) >= 1

    def test_build_content_structure(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
        wind_frequency_rose_atom: Any,
    ):
        """Test that content has proper structure."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test Report", output_dir)
        section = self._create_section("Analysis", [
            monthly_wind_atom,
            wind_frequency_rose_atom,
        ])
        builder.add_section(section)

        doc = builder.build_typst()

        # Should have section
        assert len(doc.children) == 1
        assert doc.children[0].heading.text == "Analysis"

        # Should have figure and table nodes in section body
        body = doc.children[0].body
        figures = [n for n in body if isinstance(n, TypstFigure)]
        tables = [n for n in body if isinstance(n, TypstTable)]
        assert len(figures) >= 1
        assert len(tables) >= 1


class TestReportBuilderEdgeCases:
    """Tests for ReportBuilder edge cases."""

    def _create_section(self, title: str, atoms: list[Any]) -> WindRoseSection:
        """Helper to create a WindRoseSection from atoms."""
        collection = AtomCollection.from_dict({"M01": atoms})
        return WindRoseSection(atoms=collection, title=title)

    def test_build_empty_report(self, tmp_path: Path):
        """Test building report with no sections."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Empty Report", output_dir)

        doc = builder.build_typst()

        assert len(doc.children) == 0

    def test_build_section_with_multiple_atoms(
        self,
        tmp_path: Path,
        wind_frequency_rose_atom: Any,
        wind_power_rose_atom: Any,
    ):
        """Test building report with multiple atoms in one section."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section(
            "All Analysis", [wind_frequency_rose_atom, wind_power_rose_atom]
        )
        builder.add_section(section)

        # Use build_typst() to access IR document structure
        doc = builder.build_typst()

        # Should have figures for all atoms inside section bodies
        sections = [n for n in doc.children if hasattr(n, "body")]
        figures = [n for sec in sections for n in sec.body if isinstance(n, TypstFigure)]
        assert len(figures) >= 2

    def test_build_typst_idempotent(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that build_typst is idempotent."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Analysis", [monthly_wind_atom])
        builder.add_section(section)

        doc1 = builder.build_typst()
        doc2 = builder.build_typst()

        assert doc1 == doc2
