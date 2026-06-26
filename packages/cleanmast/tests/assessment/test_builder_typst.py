"""RED-phase TDD tests for AssessmentReportBuilder.build_typst() method.

These tests define the expected behavior of the build_typst() method which
returns a domain-level TypstDocument IR tree. All tests should FAIL initially
(RED phase) because the method doesn't exist yet.

Dependencies:
    - Domain IR types: TypstDocument, TypstTable, TypstFigure, TypstHeading,
      TypstParagraph, TypstChild
    - AssessmentReportBuilder from infrastructure
    - Existing fixtures from conftest.py
"""

from pathlib import Path
from typing import Any

from cleanmast.subdomains.assessment.subdomains.wind_rose.services.wind_rose_section import (
    WindRoseSection,
)
from cleanmast.subdomains.assessment.shared.ir_types import (
    TypstDocument,
    TypstFigure,
    TypstHeading,
    TypstParagraph,
    TypstTable,
)
from cleanmast.subdomains.assessment.domain.value_objects import AtomCollection
from cleanmast.subdomains.assessment.infrastructure import AssessmentReportBuilder


class TestBuildTypstReturnsTypstDocument:
    """Tests for build_typst() return type and basic structure."""

    def _create_section(self, title: str, atoms: list[Any]) -> WindRoseSection:
        """Helper to create a WindRoseSection from atoms."""
        collection = AtomCollection.from_dict({"M01": atoms})
        return WindRoseSection(atoms=collection, title=title)

    def test_build_typst_returns_typst_document(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that build_typst() returns a TypstDocument instance.

        The build_typst() method should return a domain-level TypstDocument
        IR tree that can be serialized independently of the builder.
        """
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test Report", output_dir)
        section = self._create_section("Wind Analysis", [monthly_wind_atom])
        builder.add_section(section)

        result = builder.build_typst()

        assert isinstance(result, TypstDocument), (
            f"Expected TypstDocument, got {type(result).__name__}"
        )

    def test_build_typst_without_sections(self, tmp_path: Path):
        """Test build_typst() behavior when no sections have been added.

        When called without any sections, build_typst() should still return
        a valid TypstDocument (likely with just a title heading).
        """
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Empty Report", output_dir)

        result = builder.build_typst()

        assert isinstance(result, TypstDocument), (
            f"Expected TypstDocument for empty report, got {type(result).__name__}"
        )


class TestTypstDocumentChildrenStructure:
    """Tests for TypstDocument.children structure and content."""

    def _create_section(self, title: str, atoms: list[Any]) -> WindRoseSection:
        """Helper to create a WindRoseSection from atoms."""
        collection = AtomCollection.from_dict({"M01": atoms})
        return WindRoseSection(atoms=collection, title=title)

    def test_typst_document_has_children(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that TypstDocument.children is a non-empty list for valid input.

        A document with content should have children containing headings,
        figures, tables, and paragraphs.
        """
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test Report", output_dir)
        section = self._create_section("Wind Analysis", [monthly_wind_atom])
        builder.add_section(section)

        document = builder.build_typst()

        assert hasattr(document, "children"), "TypstDocument should have 'children' attribute"
        assert isinstance(document.children, list), "children should be a list"
        assert len(document.children) > 0, "children should not be empty for valid input"

    def test_children_contain_correct_types(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
        wind_frequency_rose_atom: Any,
    ):
        """Test that children list contains expected IR node types.

        The document should contain a mix of:
        - TypstHeading: for section titles
        - TypstFigure: for generated images/charts
        - TypstTable: for data tables
        - TypstParagraph: for text summaries
        """
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test Report", output_dir)
        section = self._create_section(
            "Analysis", [monthly_wind_atom, wind_frequency_rose_atom]
        )
        builder.add_section(section)

        document = builder.build_typst()
        children = document.children

        # Check that we have the expected types (traverse into TypstSection bodies)
        type_counts = {
            TypstHeading: 0,
            TypstFigure: 0,
            TypstTable: 0,
            TypstParagraph: 0,
        }

        def _count_node(node: Any) -> None:
            for typ in type_counts:
                if isinstance(node, typ):
                    type_counts[typ] += 1
                    break

        for child in children:
            _count_node(child)
            if hasattr(child, "heading"):
                _count_node(child.heading)
            if hasattr(child, "body"):
                for body_child in child.body:
                    _count_node(body_child)
            if hasattr(child, "subsections"):
                for sub in child.subsections:
                    _count_node(sub)
                    if hasattr(sub, "heading"):
                        _count_node(sub.heading)
                    if hasattr(sub, "body"):
                        for body_child in sub.body:
                            _count_node(body_child)

        # Should have at least one heading (for the section title)
        assert type_counts[TypstHeading] >= 1, (
            f"Expected at least 1 heading, got {type_counts[TypstHeading]}"
        )

        # Should have at least one figure (for the wind rose)
        assert type_counts[TypstFigure] >= 1, (
            f"Expected at least 1 figure, got {type_counts[TypstFigure]}"
        )

        # Should have at least one table (for frequency data)
        assert type_counts[TypstTable] >= 1, (
            f"Expected at least 1 table, got {type_counts[TypstTable]}"
        )


class TestTypstFigurePaths:
    """Tests for TypstFigure content paths."""

    def _create_section(self, title: str, atoms: list[Any]) -> WindRoseSection:
        """Helper to create a WindRoseSection from atoms."""
        collection = AtomCollection.from_dict({"M01": atoms})
        return WindRoseSection(atoms=collection, title=title)

    def test_typst_figure_paths_are_posix(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
        wind_frequency_rose_atom: Any,
    ):
        """Test that all TypstFigure.content paths use forward slashes.

        Typst requires POSIX-style paths (forward slashes) even on Windows.
        All figure content paths should be normalized to use '/' instead of '\\'.
        """
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test Report", output_dir)
        section = self._create_section(
            "Analysis", [monthly_wind_atom, wind_frequency_rose_atom]
        )
        builder.add_section(section)

        document = builder.build_typst()

        # Collect all figure paths (traverse into TypstSection bodies)
        figure_paths: list[str] = []
        for child in document.children:
            if isinstance(child, TypstFigure):
                figure_paths.append(child.content)
            elif hasattr(child, "body"):
                for body_child in child.body:
                    if isinstance(body_child, TypstFigure):
                        figure_paths.append(body_child.content)

        # Should have some figures
        assert len(figure_paths) > 0, "Expected at least one figure in document"

        # All paths should use forward slashes
        for path in figure_paths:
            assert "\\" not in path, (
                f"Figure path contains backslash (Windows path separator): {path!r}. "
                f"All paths must use forward slashes for Typst compatibility."
            )

    def test_typst_figure_paths_are_relative(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that figure paths are relative, not absolute.

        Figure paths should be relative to the output directory to ensure
        the .typ file is portable.
        """
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test Report", output_dir)
        section = self._create_section("Analysis", [monthly_wind_atom])
        builder.add_section(section)

        document = builder.build_typst()

        for child in document.children:
            if isinstance(child, TypstFigure):
                # On Windows, absolute paths start with drive letter (e.g., C:)
                # On Unix, absolute paths start with /
                content = child.content
                assert not content.startswith(("C:", "D:", "/")), (
                    f"Figure path should be relative, not absolute: {content!r}"
                )


class TestTypstDocumentContent:
    """Tests for TypstDocument content structure."""

    def _create_section(self, title: str, atoms: list[Any]) -> WindRoseSection:
        """Helper to create a WindRoseSection from atoms."""
        collection = AtomCollection.from_dict({"M01": atoms})
        return WindRoseSection(atoms=collection, title=title)

    def test_document_has_section_headings(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that document includes headings for each section.

        Each section should produce a heading in the document.
        """
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test Report", output_dir)
        section = self._create_section("Wind Speed Analysis", [monthly_wind_atom])
        builder.add_section(section)

        document = builder.build_typst()

        # Find all section headings inside TypstSection nodes
        headings: list[TypstHeading] = []
        for child in document.children:
            if hasattr(child, "heading"):
                headings.append(child.heading)

        # Should have at least the section heading
        assert len(headings) >= 1, (
            f"Expected at least 1 section heading, got {len(headings)}"
        )

        # One heading should contain the section title
        section_titles = [h.text for h in headings if "Wind Speed Analysis" in h.text]
        assert len(section_titles) > 0, (
            f"Expected heading containing 'Wind Speed Analysis', got {[h.text for h in headings]}"
        )


class TestBuildTypstSerialization:
    """Tests for build_typst() output serialization."""

    def _create_section(self, title: str, atoms: list[Any]) -> WindRoseSection:
        """Helper to create a WindRoseSection from atoms."""
        collection = AtomCollection.from_dict({"M01": atoms})
        return WindRoseSection(atoms=collection, title=title)

    def test_serialization_produces_typst_markup(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
    ):
        """Test that TypstDocument can be serialized to Typst markup.

        The document should produce valid Typst markup when serialized,
        including proper heading syntax, figure blocks, and table syntax.
        """
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test Report", output_dir)
        section = self._create_section("Analysis", [monthly_wind_atom])
        builder.add_section(section)

        document = builder.build_typst()

        # Simple serialization: just check that children can be stringified
        # In the real implementation, this would use a proper serializer
        markup_parts: list[str] = []
        for child in document.children:
            if hasattr(child, "heading"):
                markup_parts.append(f"= {child.heading.text}")
                for body_child in child.body:
                    if isinstance(body_child, TypstFigure):
                        markup_parts.append(f"#figure(image(\"{body_child.content}\"))")
                    elif isinstance(body_child, TypstTable):
                        markup_parts.append("#table(...)")
                    elif isinstance(body_child, TypstParagraph):
                        markup_parts.append(body_child.text)
            elif isinstance(child, TypstHeading):
                markup_parts.append(f"= {child.text}")
            elif isinstance(child, TypstFigure):
                markup_parts.append(f"#figure(image(\"{child.content}\"))")
            elif isinstance(child, TypstTable):
                markup_parts.append("#table(...)")
            elif isinstance(child, TypstParagraph):
                markup_parts.append(child.text)

        markup = "\n\n".join(markup_parts)

        # Should produce some Typst-like content
        assert len(markup) > 0, "Serialized markup should not be empty"
        assert "=" in markup, "Markup should contain heading syntax"

    def test_serialization_includes_all_children(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
        wind_frequency_rose_atom: Any,
    ):
        """Test that serialization includes all document children.

        Every child node in the document should be represented in the output.
        """
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test Report", output_dir)
        section = self._create_section(
            "Analysis", [monthly_wind_atom, wind_frequency_rose_atom]
        )
        builder.add_section(section)

        document = builder.build_typst()
        child_count = len(document.children)

        # Count how many children we can identify (traverse into TypstSection bodies)
        serialized_count = 0
        for child in document.children:
            if isinstance(child, (TypstHeading, TypstFigure, TypstTable, TypstParagraph)):
                serialized_count += 1
            elif hasattr(child, "heading"):
                serialized_count += 1
                for body_child in child.body:
                    if isinstance(body_child, (TypstHeading, TypstFigure, TypstTable, TypstParagraph)):
                        serialized_count += 1

        assert serialized_count >= child_count, (
            f"Expected at least {child_count} serialized children, got {serialized_count}"
        )


class TestBuildTypstMultipleSections:
    """Tests for build_typst() with multiple sections."""

    def _create_section(self, title: str, atoms: list[Any]) -> WindRoseSection:
        """Helper to create a WindRoseSection from atoms."""
        collection = AtomCollection.from_dict({"M01": atoms})
        return WindRoseSection(atoms=collection, title=title)

    def test_multiple_sections_produce_multiple_headings(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
        monthly_wind_power_atom: Any,
    ):
        """Test that multiple sections produce multiple section headings.

        Each section added should result in a corresponding heading in the output.
        """
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test Report", output_dir)

        section1 = self._create_section("Wind Speed", [monthly_wind_atom])
        section2 = self._create_section("Wind Power", [monthly_wind_power_atom])

        builder.add_section(section1).add_section(section2)

        document = builder.build_typst()

        # Find section headings inside TypstSection nodes
        sections = [c for c in document.children if hasattr(c, "heading")]
        section_headings = [sec.heading for sec in sections]

        assert len(section_headings) >= 2, (
            f"Expected at least 2 section headings, got {len(section_headings)}"
        )

        section_titles = [h.text for h in section_headings]
        assert "Wind Speed" in section_titles or any(
            "Wind Speed" in t for t in section_titles
        ), f"Expected 'Wind Speed' in headings, got {section_titles}"
        assert "Wind Power" in section_titles or any(
            "Wind Power" in t for t in section_titles
        ), f"Expected 'Wind Power' in headings, got {section_titles}"

    def test_sections_preserve_order(
        self,
        tmp_path: Path,
        monthly_wind_atom: Any,
        monthly_wind_power_atom: Any,
        wind_frequency_rose_atom: Any,
    ):
        """Test that sections appear in document in the order they were added.

        The order of children in the document should match the order of
        sections added to the builder.
        """
        output_dir = tmp_path / "output"
        builder = AssessmentReportBuilder("Test Report", output_dir)

        # Add sections in specific order
        section1 = self._create_section("First Section", [monthly_wind_atom])
        section2 = self._create_section("Second Section", [monthly_wind_power_atom])
        section3 = self._create_section("Third Section", [wind_frequency_rose_atom])

        builder.add_section(section1).add_section(section2).add_section(section3)

        document = builder.build_typst()

        # Find section headings inside TypstSection nodes
        sections = [c for c in document.children if hasattr(c, "heading")]
        section_texts = [sec.heading.text for sec in sections]

        # Find positions of our sections
        first_pos = next(
            (i for i, t in enumerate(section_texts) if "First" in t), None
        )
        second_pos = next(
            (i for i, t in enumerate(section_texts) if "Second" in t), None
        )
        third_pos = next(
            (i for i, t in enumerate(section_texts) if "Third" in t), None
        )

        assert first_pos is not None, f"Could not find First in {section_texts}"
        assert second_pos is not None, f"Could not find Second in {section_texts}"
        assert third_pos is not None, f"Could not find Third in {section_texts}"

        assert first_pos < second_pos < third_pos, (
            f"Sections not in expected order: {section_texts}"
        )
