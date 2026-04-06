"""Tests for AssessmentReportBuilder."""

from pathlib import Path
from typing import Any

from cleanmast.subdomains.assessment.domain.services.sections.wind_rose import (
    WindRoseSection,
)
from cleanmast.subdomains.assessment.domain.value_objects import AtomCollection
from cleanmast.subdomains.assessment.infrastructure import AssessmentReportBuilder


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
        return WindRoseSection(atoms=collection, title=title, level=1)

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
        return WindRoseSection(atoms=collection, title=title, level=1)

    def test_build_creates_output_directories(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that build creates output directories."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Test Section", [monthly_wind_atom])
        builder.add_section(section)

        builder.build(compile_pdf=False)

        assert output_dir.exists()
        assert (output_dir / "images").exists()

    def test_build_creates_report_typ_file(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that build creates report.typ file."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test Report", output_dir)
        section = self._create_section("Test Section", [monthly_wind_atom])
        builder.add_section(section)

        result = builder.build(compile_pdf=False)

        assert result["typ"].exists()
        assert result["typ"].name == "report.typ"
        assert result["typ"].parent == output_dir

    def test_build_returns_path(self, tmp_path: Path, monthly_wind_atom: Any):
        """Test that build returns the path to the report file."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Test", [monthly_wind_atom])
        builder.add_section(section)

        result = builder.build(compile_pdf=False)

        assert isinstance(result["typ"], Path)

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

        builder.build(compile_pdf=False)

        content = (output_dir / "report.typ").read_text(encoding="utf-8")
        assert "= Monthly Report" in content

    def test_build_content_includes_chinese_font_support(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that report includes Chinese font configuration."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Test", [monthly_wind_atom])
        builder.add_section(section)

        builder.build(compile_pdf=False)

        content = (output_dir / "report.typ").read_text(encoding="utf-8")
        assert "Source Han Serif SC" in content
        assert "Linux Libertine" in content

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

        builder.build(compile_pdf=False)

        content = (output_dir / "report.typ").read_text(encoding="utf-8")
        assert "== Wind Analysis" in content

    def test_build_content_includes_atom_summaries(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that report includes atom summaries."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Analysis", [monthly_wind_atom])
        builder.add_section(section)

        builder.build(compile_pdf=False)

        content = (output_dir / "report.typ").read_text(encoding="utf-8")
        # Summary should be in the content (contains mast name and summary text)
        assert "M01" in content

    def test_build_content_includes_figures(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that report includes figure markup."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Analysis", [monthly_wind_atom])
        builder.add_section(section)

        builder.build(compile_pdf=False)

        content = (output_dir / "report.typ").read_text(encoding="utf-8")
        assert "#figure(" in content
        assert "image(" in content

    def test_build_content_includes_tables(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that report includes table markup."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Analysis", [monthly_wind_atom])
        builder.add_section(section)

        builder.build(compile_pdf=False)

        content = (output_dir / "report.typ").read_text(encoding="utf-8")
        assert "table(" in content

    def test_build_content_includes_references(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that report includes figure references."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Analysis", [monthly_wind_atom])
        builder.add_section(section)

        builder.build(compile_pdf=False)

        content = (output_dir / "report.typ").read_text(encoding="utf-8")
        # Template uses "由图" (from figure) and "和表" (and table) for references
        assert "由图" in content
        assert "@fig-" in content

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

        builder.build(compile_pdf=False)

        content = (output_dir / "report.typ").read_text(encoding="utf-8")
        assert "== Wind Speed" in content
        assert "== Wind Power" in content

    def test_build_generates_images(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that build generates image files."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Analysis", [monthly_wind_atom])
        builder.add_section(section)

        builder.build(compile_pdf=False)

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

        builder.build(compile_pdf=False)

        content = (output_dir / "report.typ").read_text(encoding="utf-8")

        # Should have preamble
        assert "#set text(" in content
        assert "#set heading(" in content

        # Should have title
        assert "= Test Report" in content

        # Should have section
        assert "== Analysis" in content

        # Should have figure and table markup (actual counts depend on template)
        assert content.count("#figure(") >= 1
        assert content.count("table(") >= 1


class TestReportBuilderEdgeCases:
    """Tests for ReportBuilder edge cases."""

    def _create_section(self, title: str, atoms: list[Any]) -> WindRoseSection:
        """Helper to create a WindRoseSection from atoms."""
        collection = AtomCollection.from_dict({"M01": atoms})
        return WindRoseSection(atoms=collection, title=title, level=1)

    def test_build_empty_report(self, tmp_path: Path):
        """Test building report with no sections."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Empty Report", output_dir)

        builder.build(compile_pdf=False)

        content = (output_dir / "report.typ").read_text(encoding="utf-8")
        assert "= Empty Report" in content
        assert "#set text(" in content

    def test_build_section_with_multiple_atoms(
        self,
        tmp_path: Path,
        all_atoms: list[Any],
    ):
        """Test building report with multiple atoms in one section."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("All Analysis", all_atoms)
        builder.add_section(section)

        builder.build(compile_pdf=False)

        content = (output_dir / "report.typ").read_text(encoding="utf-8")
        # Should have figures for all atoms
        assert content.count("#figure(") >= len(all_atoms)

    def test_build_overwrites_existing_report(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that build overwrites existing report file."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        report_file = output_dir / "report.typ"
        report_file.write_text("Old content", encoding="utf-8")

        builder = AssessmentReportBuilder("New Report", output_dir)
        section = self._create_section("Test", [monthly_wind_atom])
        builder.add_section(section)
        builder.build(compile_pdf=False)

        content = report_file.read_text(encoding="utf-8")
        assert "New Report" in content
        assert "Old content" not in content

    def test_build_idempotent(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that build is idempotent."""
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test", output_dir)
        section = self._create_section("Analysis", [monthly_wind_atom])
        builder.add_section(section)

        result1 = builder.build(compile_pdf=False)
        content1 = result1["typ"].read_text(encoding="utf-8")

        result2 = builder.build(compile_pdf=False)
        content2 = result2["typ"].read_text(encoding="utf-8")

        assert content1 == content2
