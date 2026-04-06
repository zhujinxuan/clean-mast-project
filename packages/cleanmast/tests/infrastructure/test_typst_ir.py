"""Typst IR node tests - RED phase (tests before implementation).

Tests for IR node construction, validation, serialization, and golden snapshot compilation.
Follows TDD: RED (write failing tests) -> GREEN (make tests pass) -> REFACTOR.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from cleanmast.infrastructure.typst_ir import serialize
from cleanmast.subdomains.assessment.domain.types import (
    TypstDocument,
    TypstFigure,
    TypstHeading,
    TypstParagraph,
    TypstTable,
)

TYPST_AVAILABLE = shutil.which("typst") is not None
SNAPSHOT_DIR = Path(__file__).parent.parent / "assessment" / "snapshots"
TEMP_DIR = Path(__file__).parent.parent.parent.parent.parent / "temp" / "2026-04-04-typst-ir-verification"


class TestTypstTableNode:
    """Test TypstTable IR node construction and validation."""

    def test_table_construction_basic(self) -> None:
        """Test basic table construction with required fields."""
        table = TypstTable(
            data=[["1", "2"], ["3", "4"]],
            headers=["Col1", "Col2"],
        )
        assert table.data == [["1", "2"], ["3", "4"]]
        assert table.headers == ["Col1", "Col2"]
        assert table.caption is None

    def test_table_construction_with_caption(self) -> None:
        """Test table construction with optional caption."""
        table = TypstTable(
            data=[["a", "b"]],
            headers=["A", "B"],
            caption="Test Table",
        )
        assert table.caption == "Test Table"

    def test_table_frozen(self) -> None:
        """Test that table nodes are immutable (frozen dataclass)."""
        table = TypstTable(
            data=[["1"]],
            headers=["Col"],
        )
        with pytest.raises(AttributeError):
            table.caption = "New Caption"  # type: ignore

    def test_table_empty_data_validation(self) -> None:
        """Test that empty data raises validation error during serialization."""
        table = TypstTable(data=[], headers=["Col"])
        # Empty data should be validated during serialization
        with pytest.raises(ValueError, match="empty"):
            _ = table_to_typst(table)

    def test_table_headers_length_mismatch(self) -> None:
        """Test that header/data column mismatch raises error."""
        table = TypstTable(
            data=[["1", "2", "3"]],  # 3 columns
            headers=["A", "B"],  # 2 columns
        )
        with pytest.raises(ValueError, match="header|column"):
            _ = table_to_typst(table)


class TestTypstFigureNode:
    """Test TypstFigure IR node construction and validation."""

    def test_figure_construction_basic(self) -> None:
        """Test basic figure construction."""
        fig = TypstFigure(
            content="images/chart.png",
            caption="Wind Speed Chart",
        )
        assert fig.content == "images/chart.png"
        assert fig.caption == "Wind Speed Chart"
        assert fig.kind == "image"

    def test_figure_construction_with_kind(self) -> None:
        """Test figure construction with custom kind."""
        fig = TypstFigure(
            content="custom/diagram.svg",
            caption="Diagram",
            kind="diagram",
        )
        assert fig.kind == "diagram"

    def test_figure_frozen(self) -> None:
        """Test that figure nodes are immutable."""
        fig = TypstFigure(content="img.png", caption="Caption")
        with pytest.raises(AttributeError):
            fig.caption = "New"  # type: ignore

    def test_figure_empty_content_validation(self) -> None:
        """Test that empty content raises validation error."""
        fig = TypstFigure(content="", caption="Empty")
        with pytest.raises(ValueError, match="content"):
            _ = figure_to_typst(fig)


class TestTypstHeadingNode:
    """Test TypstHeading IR node construction and heading normalization."""

    def test_heading_construction_level1(self) -> None:
        """Test level 1 heading (default)."""
        h = TypstHeading(text="Introduction")
        assert h.text == "Introduction"
        assert h.level == 1

    def test_heading_construction_level2(self) -> None:
        """Test level 2 heading."""
        h = TypstHeading(text="Background", level=2)
        assert h.level == 2

    def test_heading_construction_level3(self) -> None:
        """Test level 3 heading."""
        h = TypstHeading(text="Details", level=3)
        assert h.level == 3

    def test_heading_level_bounds(self) -> None:
        """Test that levels outside 1-3 are clamped or validated."""
        # Level 0 should raise error or be normalized to 1
        h = TypstHeading(text="Title", level=0)
        # During serialization, should normalize or error
        result = heading_to_typst(h)
        assert result.startswith("= ")  # Normalized to level 1

    def test_heading_frozen(self) -> None:
        """Test that heading nodes are immutable."""
        h = TypstHeading(text="Title")
        with pytest.raises(AttributeError):
            h.text = "New"  # type: ignore


class TestTypstParagraphNode:
    """Test TypstParagraph IR node construction."""

    def test_paragraph_construction(self) -> None:
        """Test basic paragraph construction."""
        p = TypstParagraph(text="This is a paragraph.")
        assert p.text == "This is a paragraph."

    def test_paragraph_frozen(self) -> None:
        """Test that paragraph nodes are immutable."""
        p = TypstParagraph(text="Text")
        with pytest.raises(AttributeError):
            p.text = "New"  # type: ignore


class TestTypstDocumentNode:
    """Test TypstDocument IR node construction and nesting."""

    def test_document_empty(self) -> None:
        """Test empty document construction."""
        doc = TypstDocument(children=[])
        assert doc.children == []

    def test_document_with_children(self) -> None:
        """Test document with mixed children."""
        doc = TypstDocument(
            children=[
                TypstHeading(text="Section 1", level=1),
                TypstParagraph(text="Introduction text."),
                TypstTable(
                    data=[["1", "2"]],
                    headers=["A", "B"],
                ),
            ]
        )
        assert len(doc.children) == 3
        assert isinstance(doc.children[0], TypstHeading)
        assert isinstance(doc.children[1], TypstParagraph)
        assert isinstance(doc.children[2], TypstTable)

    def test_document_nested_structure(self) -> None:
        """Test document with heading → paragraph → table nesting."""
        doc = TypstDocument(
            children=[
                TypstHeading(text="Main Title", level=1),
                TypstParagraph(text="Summary paragraph."),
                TypstHeading(text="Subsection", level=2),
                TypstTable(
                    data=[["N", "10"], ["S", "20"]],
                    headers=["Dir", "Speed"],
                    caption="Wind Data",
                ),
                TypstFigure(
                    content="images/chart.png",
                    caption="Chart",
                ),
            ]
        )
        assert len(doc.children) == 5

    def test_document_frozen(self) -> None:
        """Test that document nodes are immutable."""
        doc = TypstDocument(children=[])
        with pytest.raises(AttributeError):
            doc.children = []  # type: ignore


class TestSerializer:
    """Test Typst IR serializer."""

    def test_serialize_table_basic(self) -> None:
        """Test serializing a basic table."""
        table = TypstTable(
            data=[["N", "80m", "10"]],
            headers=["Dir", "Height", "Speed"],
        )
        result = serialize(TypstDocument(children=[table]))
        assert "#table(" in result
        assert "columns:" in result
        assert "table.header(" in result
        assert "[Dir]" in result
        assert "[N]" in result

    def test_serialize_table_with_caption(self) -> None:
        """Test serializing a table with caption."""
        table = TypstTable(
            data=[["1"]],
            headers=["A"],
            caption="Table 1",
        )
        result = serialize(TypstDocument(children=[table]))
        assert "#figure(" in result
        assert "caption: [Table 1]" in result
        assert "#table(" in result

    def test_serialize_figure(self) -> None:
        """Test serializing a figure."""
        fig = TypstFigure(
            content="images/wind.png",
            caption="Wind Chart",
        )
        result = serialize(TypstDocument(children=[fig]))
        assert "#figure(" in result
        assert 'image("images/wind.png"' in result
        assert "caption: [Wind Chart]" in result

    def test_serialize_heading_levels(self) -> None:
        """Test heading level serialization produces correct markers."""
        doc = TypstDocument(
            children=[
                TypstHeading(text="Level 1", level=1),
                TypstHeading(text="Level 2", level=2),
                TypstHeading(text="Level 3", level=3),
            ]
        )
        result = serialize(doc)
        assert "= Level 1" in result
        assert "== Level 2" in result
        assert "=== Level 3" in result

    def test_serialize_paragraph(self) -> None:
        """Test serializing a paragraph."""
        p = TypstParagraph(text="Hello world.")
        result = serialize(TypstDocument(children=[p]))
        assert "Hello world." in result

    def test_serialize_full_document(self) -> None:
        """Test serializing a complete document with all node types."""
        doc = TypstDocument(
            children=[
                TypstHeading(text="Report", level=1),
                TypstParagraph(text="This is the introduction."),
                TypstHeading(text="Data", level=2),
                TypstTable(
                    data=[["a", "b"]],
                    headers=["Col1", "Col2"],
                ),
                TypstFigure(
                    content="fig.png",
                    caption="Figure",
                ),
            ]
        )
        result = serialize(doc)
        # Verify structure
        assert "= Report" in result
        assert "This is the introduction." in result
        assert "== Data" in result
        assert "#table(" in result
        assert "#figure(" in result

    def test_serialize_rejects_non_document_root(self) -> None:
        """Test that serializer rejects non-TypstDocument root."""
        with pytest.raises(TypeError, match="TypstDocument"):
            serialize(TypstTable(data=[["1"]], headers=["A"]))  # type: ignore

    def test_serialize_rejects_invalid_children(self) -> None:
        """Test that serializer rejects invalid child types."""
        doc = TypstDocument(children=["invalid"])  # type: ignore
        with pytest.raises(TypeError):
            serialize(doc)


class TestGoldenSnapshotCompilation:
    """Golden gate tests: compile existing .typ snapshots from IR."""

    def compile_typst(self, typ_content: str, output_path: Path) -> tuple[bool, str]:
        """Compile Typst content to PDF."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_typ_file = output_path.with_suffix(".typ")
        temp_typ_file.write_text(typ_content, encoding="utf-8")

        try:
            result = subprocess.run(
                ["typst", "compile", str(temp_typ_file), str(output_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Compilation timed out"
        except Exception as e:
            return False, str(e)

    def read_snapshot(self, name: str) -> str:
        """Read golden snapshot file."""
        path = SNAPSHOT_DIR / f"{name}.typ"
        return path.read_text(encoding="utf-8")

    @pytest.mark.skipif(not TYPST_AVAILABLE, reason="typst CLI not available")
    def test_golden_snapshot_turbulence_sector(self, tmp_path: Path) -> None:
        """Golden gate: turbulence_sector.typ compiles from IR."""
        # Parse the snapshot to understand structure
        self.read_snapshot("turbulence_sector")

        # Construct equivalent IR
        # Table has 5 columns: 风向, 高度, 平均TI(%), 代表TI(%), IEC类别
        headers = ["风向", "高度", "平均TI(%)", "代表TI(%)", "IEC类别"]
        data = [
            ["N", "80m", "15.00", "18.00", "B"],
            ["N", "120m 外推", "15.00", "18.00", "B"],
            ["NNE", "80m", "12.00", "15.00", "B"],
            ["NNE", "120m 外推", "12.00", "15.00", "B"],
            ["NE", "80m", "12.00", "15.00", "B"],
            ["NE", "120m 外推", "12.00", "15.00", "B"],
            ["ENE", "80m", "12.00", "15.00", "B"],
            ["ENE", "120m 外推", "12.00", "15.00", "B"],
            ["E", "80m", "12.00", "15.00", "B"],
            ["E", "120m 外推", "12.00", "15.00", "B"],
            ["ESE", "80m", "12.00", "15.00", "B"],
            ["ESE", "120m 外推", "12.00", "15.00", "B"],
            ["SE", "80m", "12.00", "15.00", "B"],
            ["SE", "120m 外推", "12.00", "15.00", "B"],
            ["SSE", "80m", "12.00", "15.00", "B"],
            ["SSE", "120m 外推", "12.00", "15.00", "B"],
            ["S", "80m", "12.00", "15.00", "B"],
            ["S", "120m 外推", "12.00", "15.00", "B"],
            ["SSW", "80m", "12.00", "15.00", "B"],
            ["SSW", "120m 外推", "12.00", "15.00", "B"],
            ["SW", "80m", "12.00", "15.00", "B"],
            ["SW", "120m 外推", "12.00", "15.00", "B"],
            ["WSW", "80m", "12.00", "15.00", "B"],
            ["WSW", "120m 外推", "12.00", "15.00", "B"],
            ["W", "80m", "12.00", "15.00", "B"],
            ["W", "120m 外推", "12.00", "15.00", "B"],
            ["WNW", "80m", "12.00", "15.00", "B"],
            ["WNW", "120m 外推", "12.00", "15.00", "B"],
            ["NW", "80m", "12.00", "15.00", "B"],
            ["NW", "120m 外推", "12.00", "15.00", "B"],
            ["NNW", "80m", "12.00", "15.00", "B"],
            ["NNW", "120m 外推", "12.00", "15.00", "B"],
        ]

        doc = TypstDocument(
            children=[
                TypstTable(data=data, headers=headers),
            ]
        )

        serialized = serialize(doc)
        output_pdf = TEMP_DIR / "turbulence_sector_ir.pdf"
        success, error = self.compile_typst(serialized, output_pdf)

        assert success, f"Typst compilation failed: {error}"
        assert output_pdf.exists(), "PDF was not created"

    @pytest.mark.skipif(not TYPST_AVAILABLE, reason="typst CLI not available")
    def test_golden_snapshot_vertical_profile(self, tmp_path: Path) -> None:
        """Golden gate: vertical_profile.typ compiles from IR."""
        headers = ["高度", "平均风速(m/s)", "风切变指数α", "拟合优度R²"]
        data = [
            ["50m", "5.20", "0.150", "0.980"],
            ["80m", "6.10", "0.150", "0.980"],
            ["100m", "6.80", "0.150", "0.980"],
            ["120m 外推", "7.20", "0.150", "0.980"],
        ]

        doc = TypstDocument(
            children=[
                TypstTable(data=data, headers=headers),
            ]
        )

        serialized = serialize(doc)
        output_pdf = TEMP_DIR / "vertical_profile_ir.pdf"
        success, error = self.compile_typst(serialized, output_pdf)

        assert success, f"Typst compilation failed: {error}"
        assert output_pdf.exists(), "PDF was not created"

    @pytest.mark.skipif(not TYPST_AVAILABLE, reason="typst CLI not available")
    def test_golden_snapshot_weibull_distribution(self, tmp_path: Path) -> None:
        """Golden gate: weibull_distribution.typ compiles from IR."""
        headers = ["高度", "形状参数k", "尺度参数c(m/s)", "平均风速(m/s)"]
        data = [
            ["80m", "2.100", "7.500", "6.80"],
            ["120m 外推", "2.300", "8.200", "7.50"],
        ]

        doc = TypstDocument(
            children=[
                TypstTable(data=data, headers=headers),
            ]
        )

        serialized = serialize(doc)
        output_pdf = TEMP_DIR / "weibull_distribution_ir.pdf"
        success, error = self.compile_typst(serialized, output_pdf)

        assert success, f"Typst compilation failed: {error}"
        assert output_pdf.exists(), "PDF was not created"

    @pytest.mark.skipif(not TYPST_AVAILABLE, reason="typst CLI not available")
    def test_golden_snapshot_wind_frequency_rose(self, tmp_path: Path) -> None:
        """Golden gate: wind_frequency_rose.typ compiles from IR."""
        headers = ["风向", "80m", "120m 外推"]
        data = [
            ["N", "20.00", "20.00"],
            ["NNE", "5.00", "5.00"],
            ["NE", "5.00", "5.00"],
            ["ENE", "5.00", "5.00"],
            ["E", "5.00", "5.00"],
            ["ESE", "5.00", "5.00"],
            ["SE", "5.00", "5.00"],
            ["SSE", "5.00", "5.00"],
            ["S", "5.00", "5.00"],
            ["SSW", "5.00", "5.00"],
            ["SW", "5.00", "5.00"],
            ["WSW", "5.00", "5.00"],
            ["W", "5.00", "5.00"],
            ["WNW", "5.00", "5.00"],
            ["NW", "5.00", "5.00"],
            ["NNW", "5.00", "5.00"],
        ]

        doc = TypstDocument(
            children=[
                TypstTable(data=data, headers=headers),
            ]
        )

        serialized = serialize(doc)
        output_pdf = TEMP_DIR / "wind_frequency_rose_ir.pdf"
        success, error = self.compile_typst(serialized, output_pdf)

        assert success, f"Typst compilation failed: {error}"
        assert output_pdf.exists(), "PDF was not created"

    @pytest.mark.skipif(not TYPST_AVAILABLE, reason="typst CLI not available")
    def test_golden_snapshot_wind_power_rose(self, tmp_path: Path) -> None:
        """Golden gate: wind_power_rose.typ compiles from IR."""
        headers = ["风向", "80m", "120m 外推"]
        data = [
            ["N", "300.00", "300.00"],
            ["NNE", "100.00", "100.00"],
            ["NE", "100.00", "100.00"],
            ["ENE", "100.00", "100.00"],
            ["E", "100.00", "100.00"],
            ["ESE", "100.00", "100.00"],
            ["SE", "100.00", "100.00"],
            ["SSE", "100.00", "100.00"],
            ["S", "100.00", "100.00"],
            ["SSW", "100.00", "100.00"],
            ["SW", "100.00", "100.00"],
            ["WSW", "100.00", "100.00"],
            ["W", "100.00", "100.00"],
            ["WNW", "100.00", "100.00"],
            ["NW", "100.00", "100.00"],
            ["NNW", "100.00", "100.00"],
        ]

        doc = TypstDocument(
            children=[
                TypstTable(data=data, headers=headers),
            ]
        )

        serialized = serialize(doc)
        output_pdf = TEMP_DIR / "wind_power_rose_ir.pdf"
        success, error = self.compile_typst(serialized, output_pdf)

        assert success, f"Typst compilation failed: {error}"
        assert output_pdf.exists(), "PDF was not created"


# Helper functions for serialization tests (called before full serializer is implemented)
def table_to_typst(table: TypstTable) -> str:
    """Convert table to Typst - will be replaced by full serializer."""
    return serialize(TypstDocument(children=[table]))


def figure_to_typst(fig: TypstFigure) -> str:
    """Convert figure to Typst - will be replaced by full serializer."""
    return serialize(TypstDocument(children=[fig]))


def heading_to_typst(heading: TypstHeading) -> str:
    """Convert heading to Typst - will be replaced by full serializer."""
    return serialize(TypstDocument(children=[heading]))
