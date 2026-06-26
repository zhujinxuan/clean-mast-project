"""Tests for subsection_renderer utility.

TDD coverage:
- Empty summaries skipped
- Missing tables skipped
- Missing figures skipped
- Multi-mast ordering (all paragraphs before tables before figures)
- has_summary=False skips text phase
"""

from pathlib import Path

import polars as pl
from cleanmast.subdomains.assessment.shared.protocols.report_atom import ReportAtom
from cleanmast.subdomains.assessment.shared.utils.subsection_renderer import (
    render_subsection_content,
)
from cleanmast.subdomains.assessment.shared.ir_types import (
    TypstFigure,
    TypstParagraph,
    TypstTable,
)
from cleanmast.subdomains.assessment.domain.value_objects import AtomCollection


class MockSchema:
    """Mock schema for testing."""

    @classmethod
    def validate(cls, df: pl.DataFrame, *, cast: bool = False) -> pl.DataFrame:
        return df


class MockMeta:
    """Mock metadata for testing."""

    caption: str | None = None

    def __init__(self, mast_name: str):
        self.mast_name = mast_name


class TextAtom(ReportAtom[MockSchema, MockMeta]):
    """Atom that renders only text."""

    def renderTable(self) -> TypstTable | None:
        return None

    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return output_dir / "text.png"

    def renderSummary(self) -> list[TypstParagraph]:
        return [TypstParagraph(text=f"text from {self.meta.mast_name}")]

    def renderImageTypst(self, output_dir: Path, force: bool = False) -> TypstFigure | None:
        return None


class TableAtom(ReportAtom[MockSchema, MockMeta]):
    """Atom that renders only a table."""

    def renderTable(self) -> TypstTable | None:
        return TypstTable(
            headers=["Col"],
            data=[[f"table from {self.meta.mast_name}"]],
        )

    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return output_dir / "table.png"

    def renderSummary(self) -> list[TypstParagraph]:
        return []


class FigureAtom(ReportAtom[MockSchema, MockMeta]):
    """Atom that renders only a figure."""

    def renderTable(self) -> TypstTable | None:
        return None

    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return output_dir / f"fig_{self.meta.mast_name}.png"

    def renderSummary(self) -> list[TypstParagraph]:
        return []

    def renderImageTypst(self, output_dir: Path, force: bool = False) -> TypstFigure | None:
        image_path = self.renderImage(output_dir, force)
        rel_path = image_path.relative_to(output_dir.parent)
        return TypstFigure(content=rel_path.as_posix(), caption="Figure")


class FullAtom(ReportAtom[MockSchema, MockMeta]):
    """Atom that renders text, table, and figure."""

    def renderTable(self) -> TypstTable | None:
        return TypstTable(
            headers=["Col"],
            data=[[f"table from {self.meta.mast_name}"]],
        )

    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return output_dir / f"fig_{self.meta.mast_name}.png"

    def renderSummary(self) -> list[TypstParagraph]:
        return [TypstParagraph(text=f"summary from {self.meta.mast_name}")]

    def renderImageTypst(self, output_dir: Path, force: bool = False) -> TypstFigure | None:
        image_path = self.renderImage(output_dir, force)
        rel_path = image_path.relative_to(output_dir.parent)
        return TypstFigure(content=rel_path.as_posix(), caption="Figure")


class EmptySummaryAtom(ReportAtom[MockSchema, MockMeta]):
    """Atom that renders empty summary text."""

    def renderTable(self) -> TypstTable | None:
        return None

    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return output_dir / "empty.png"

    def renderSummary(self) -> list[TypstParagraph]:
        return [TypstParagraph(text="   ")]


class NoTableAtom(ReportAtom[MockSchema, MockMeta]):
    """Atom that returns None for table."""

    def renderTable(self) -> TypstTable | None:
        return None

    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return output_dir / "no_table.png"

    def renderSummary(self) -> list[TypstParagraph]:
        return [TypstParagraph(text=f"no table {self.meta.mast_name}")]


class NoFigureAtom(ReportAtom[MockSchema, MockMeta]):
    """Atom that returns None for figure."""

    def renderTable(self) -> TypstTable | None:
        return TypstTable(
            headers=["Col"],
            data=[[f"no figure {self.meta.mast_name}"]],
        )

    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return output_dir / "no_figure.png"

    def renderSummary(self) -> list[TypstParagraph]:
        return [TypstParagraph(text=f"no figure {self.meta.mast_name}")]

    def renderImageTypst(self, output_dir: Path, force: bool = False) -> TypstFigure | None:
        return None


def _create_atom(atom_class: type[ReportAtom], mast_name: str) -> ReportAtom:
    df = pl.DataFrame({"col": [1, 2, 3]})
    meta = MockMeta(mast_name)
    atom = atom_class.__new__(atom_class)
    atom.df = df
    atom.schema = MockSchema
    atom.meta = meta
    atom._df_hashkey = None
    return atom


class TestRenderSubsectionContent:
    def test_empty_summaries_skipped(self, tmp_path: Path) -> None:
        atom1 = _create_atom(EmptySummaryAtom, "M01")
        atom2 = _create_atom(EmptySummaryAtom, "M02")
        collection = AtomCollection.from_dict({
            "M01": [atom1],
            "M02": [atom2],
        })

        result = render_subsection_content(
            collection=collection,
            atom_configs=[(EmptySummaryAtom, True)],
            images_dir=tmp_path,
        )

        paragraphs = [b for b in result if isinstance(b, TypstParagraph)]
        assert len(paragraphs) == 0

    def test_missing_tables_skipped(self, tmp_path: Path) -> None:
        atom1 = _create_atom(NoTableAtom, "M01")
        atom2 = _create_atom(NoTableAtom, "M02")
        collection = AtomCollection.from_dict({
            "M01": [atom1],
            "M02": [atom2],
        })

        result = render_subsection_content(
            collection=collection,
            atom_configs=[(NoTableAtom, True)],
            images_dir=tmp_path,
        )

        tables = [b for b in result if isinstance(b, TypstTable)]
        assert len(tables) == 0

    def test_missing_figures_skipped(self, tmp_path: Path) -> None:
        atom1 = _create_atom(NoFigureAtom, "M01")
        atom2 = _create_atom(NoFigureAtom, "M02")
        collection = AtomCollection.from_dict({
            "M01": [atom1],
            "M02": [atom2],
        })

        result = render_subsection_content(
            collection=collection,
            atom_configs=[(NoFigureAtom, True)],
            images_dir=tmp_path,
        )

        figures = [b for b in result if isinstance(b, TypstFigure)]
        assert len(figures) == 0

    def test_multi_mast_three_phase_ordering(self, tmp_path: Path) -> None:
        atom1 = _create_atom(FullAtom, "M01")
        atom2 = _create_atom(FullAtom, "M02")
        collection = AtomCollection.from_dict({
            "M01": [atom1],
            "M02": [atom2],
        })

        result = render_subsection_content(
            collection=collection,
            atom_configs=[(FullAtom, True)],
            images_dir=tmp_path,
        )

        assert len(result) == 5

        assert isinstance(result[0], TypstParagraph)
        assert "M01" in result[0].text
        assert "M02" in result[0].text

        assert isinstance(result[1], TypstTable)
        assert result[1].data[0][0] == "table from M01"
        assert isinstance(result[2], TypstTable)
        assert result[2].data[0][0] == "table from M02"

        assert isinstance(result[3], TypstFigure)
        assert isinstance(result[4], TypstFigure)

    def test_has_summary_false_skips_text_phase(self, tmp_path: Path) -> None:
        atom1 = _create_atom(FullAtom, "M01")
        atom2 = _create_atom(FullAtom, "M02")
        collection = AtomCollection.from_dict({
            "M01": [atom1],
            "M02": [atom2],
        })

        result = render_subsection_content(
            collection=collection,
            atom_configs=[(FullAtom, False)],
            images_dir=tmp_path,
        )

        paragraphs = [b for b in result if isinstance(b, TypstParagraph)]
        assert len(paragraphs) == 0

        tables = [b for b in result if isinstance(b, TypstTable)]
        assert len(tables) == 2

        figures = [b for b in result if isinstance(b, TypstFigure)]
        assert len(figures) == 2

    def test_multiple_atom_types_global_three_phase_ordering(self, tmp_path: Path) -> None:
        """All paragraphs from all types come before all tables from all types."""
        text1 = _create_atom(TextAtom, "M01")
        text2 = _create_atom(TextAtom, "M02")
        table1 = _create_atom(TableAtom, "M01")
        table2 = _create_atom(TableAtom, "M02")
        collection = AtomCollection.from_dict({
            "M01": [text1, table1],
            "M02": [text2, table2],
        })

        result = render_subsection_content(
            collection=collection,
            atom_configs=[
                (TextAtom, True),
                (TableAtom, True),
            ],
            images_dir=tmp_path,
        )

        # Paragraphs first (TextAtom), then tables (TextAtom has none), then paragraphs (TableAtom has none), then tables (TableAtom)
        # So: TextAtom paragraph, TableAtom table M01, TableAtom table M02
        paragraphs = [b for b in result if isinstance(b, TypstParagraph)]
        tables = [b for b in result if isinstance(b, TypstTable)]

        assert len(paragraphs) == 1
        assert len(tables) == 2

        # Verify ordering: paragraph before tables
        para_index = next(i for i, b in enumerate(result) if isinstance(b, TypstParagraph))
        first_table_index = next(i for i, b in enumerate(result) if isinstance(b, TypstTable))
        assert para_index < first_table_index

    def test_no_atoms_for_type_returns_empty(self, tmp_path: Path) -> None:
        collection = AtomCollection.from_dict({})

        result = render_subsection_content(
            collection=collection,
            atom_configs=[(FullAtom, True)],
            images_dir=tmp_path,
        )

        assert result == []

    def test_partial_content_for_atom_type(self, tmp_path: Path) -> None:
        """If some masts have content and others don't, only non-empty content is appended."""
        atom1 = _create_atom(TextAtom, "M01")
        atom2 = _create_atom(TextAtom, "M02")
        collection = AtomCollection.from_dict({
            "M01": [atom1],
            "M02": [atom2],
        })

        result = render_subsection_content(
            collection=collection,
            atom_configs=[(TextAtom, True)],
            images_dir=tmp_path,
        )

        assert len(result) == 1
        assert isinstance(result[0], TypstParagraph)
        assert "M01" in result[0].text
        assert "M02" in result[0].text
