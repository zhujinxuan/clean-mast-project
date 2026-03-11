"""Tests for ReportAtom base class."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl
import pytest
from typing_extensions import override

from cleanmast.subdomains.reporting.entities import ReportAtom, SchemaProtocol
from cleanmast.subdomains.reporting.entities import SingleMastMonthlyWindAtom, MonthlyWindSchema
from cleanmast.subdomains.reporting.value_objects import SingleMastMeta


class MockSchema:
    """Mock schema for testing."""

    @classmethod
    def validate(cls, df: pl.DataFrame, *, cast: bool = False) -> pl.DataFrame:
        """Pass-through validation for testing."""
        return df


@dataclass
class MockMeta:
    """Mock metadata for testing."""

    caption: str = "Test Caption"
    width: str = "80%"


@dataclass
class ConcreteAtom(ReportAtom[MockSchema, MockMeta]):
    """Concrete implementation of ReportAtom for testing."""

    @override
    def renderTable(self) -> str:
        return "#table(test)"

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return output_dir / "test.png"

    @override
    def renderSummary(self) -> str:
        return "Test summary"


class TestReportAtomCreate:
    """Tests for ReportAtom.create factory method."""

    def test_create_validates_dataframe(self):
        """Test that create validates the DataFrame with the schema."""
        df = pl.DataFrame({
            "month": [1, 2],
            "height": [100.0, 120.0],
            "interpolation_marker": [None, None],
            "wind_speed_mean": [5.0, 6.0],
            "wind_speed_max": [8.0, 9.0],
            "wind_speed_min": [2.0, 3.0],
        })
        meta = SingleMastMeta(mast_name="Test")

        atom = SingleMastMonthlyWindAtom.create(
            schema=MonthlyWindSchema,
            df=df,
            meta=meta,
        )

        assert atom.df is not None
        assert atom.schema == MonthlyWindSchema
        assert atom.meta == meta

    def test_create_returns_correct_type(self):
        """Test that create returns instance of the correct type."""
        df = pl.DataFrame({"col": [1, 2, 3]})
        meta = MockMeta()

        atom = ConcreteAtom.create(
            schema=MockSchema,
            df=df,
            meta=meta,
        )

        assert isinstance(atom, ConcreteAtom)
        assert atom.schema == MockSchema
        assert atom.meta.caption == "Test Caption"


class TestReportAtomHashCaching:
    """Tests for ReportAtom hash caching behavior."""

    def test_hash_computed_lazily(self):
        """Test that hash is computed only when first requested."""
        df = pl.DataFrame({"col": [1, 2, 3]})
        meta = MockMeta()

        atom = ConcreteAtom.create(
            schema=MockSchema,
            df=df,
            meta=meta,
        )

        # Hash should be None initially
        assert atom._df_hashkey is None

        # Compute hash
        hashkey = atom.get_or_compute_df_hashkey()

        # Hash should now be set and start with class name
        assert atom._df_hashkey == hashkey
        assert hashkey.startswith("ConcreteAtom_")

    def test_hash_cached_on_subsequent_calls(self):
        """Test that hash is cached and reused."""
        df = pl.DataFrame({"col": [1, 2, 3]})
        meta = MockMeta()

        atom = ConcreteAtom.create(
            schema=MockSchema,
            df=df,
            meta=meta,
        )

        hashkey1 = atom.get_or_compute_df_hashkey()
        hashkey2 = atom.get_or_compute_df_hashkey()

        # Should return same hash
        assert hashkey1 == hashkey2
        # Should be 12 hex chars after underscore
        assert len(hashkey1.split("_")[1]) == 12

    def test_different_data_produces_different_hashes(self):
        """Test that different DataFrame content produces different hashes."""
        meta = MockMeta()

        atom1 = ConcreteAtom.create(
            schema=MockSchema,
            df=pl.DataFrame({"col": [1, 2, 3]}),
            meta=meta,
        )
        atom2 = ConcreteAtom.create(
            schema=MockSchema,
            df=pl.DataFrame({"col": [4, 5, 6]}),
            meta=meta,
        )

        hash1 = atom1.get_or_compute_df_hashkey()
        hash2 = atom2.get_or_compute_df_hashkey()

        assert hash1 != hash2

    def test_same_data_produces_same_hash(self):
        """Test that identical DataFrame content produces same hash."""
        meta = MockMeta()
        df = pl.DataFrame({"col": [1, 2, 3]})

        atom1 = ConcreteAtom.create(schema=MockSchema, df=df, meta=meta)
        atom2 = ConcreteAtom.create(schema=MockSchema, df=df, meta=meta)

        hash1 = atom1.get_or_compute_df_hashkey()
        hash2 = atom2.get_or_compute_df_hashkey()

        assert hash1 == hash2


class TestReportAtomRenderImageTypst:
    """Tests for renderImageTypst method."""

    def test_render_image_typst_includes_figure_markup(self, tmp_path: Path):
        """Test that renderImageTypst generates proper Typst figure."""
        df = pl.DataFrame({"col": [1, 2, 3]})
        meta = MockMeta(caption="Test Figure", width="70%")

        atom = ConcreteAtom.create(schema=MockSchema, df=df, meta=meta)

        output_dir = tmp_path / "images"
        output_dir.mkdir()

        result = atom.renderImageTypst(output_dir)

        # Should contain figure markup
        assert "#figure(" in result
        assert "caption: [Test Figure]" in result
        assert "width: 70%" in result
        assert "test.png" in result

    def test_render_image_typst_includes_label(self, tmp_path: Path):
        """Test that renderImageTypst includes proper label reference."""
        df = pl.DataFrame({"col": [1, 2, 3]})
        meta = MockMeta()

        atom = ConcreteAtom.create(schema=MockSchema, df=df, meta=meta)
        output_dir = tmp_path / "images"
        output_dir.mkdir()

        result = atom.renderImageTypst(output_dir)
        hashkey = atom.get_or_compute_df_hashkey()

        # Should contain label with hashkey
        assert f"<fig-{hashkey}>" in result


class TestReportAtomGetReference:
    """Tests for getReference method."""

    def test_get_reference_returns_typst_format(self):
        """Test that getReference returns Typst reference format."""
        df = pl.DataFrame({"col": [1, 2, 3]})
        meta = MockMeta()

        atom = ConcreteAtom.create(schema=MockSchema, df=df, meta=meta)
        reference = atom.getReference()
        hashkey = atom.get_or_compute_df_hashkey()

        assert reference == f"@fig-{hashkey}"
        assert reference.startswith("@fig-")

    def test_get_reference_consistent(self):
        """Test that getReference returns consistent value."""
        df = pl.DataFrame({"col": [1, 2, 3]})
        meta = MockMeta()

        atom = ConcreteAtom.create(schema=MockSchema, df=df, meta=meta)

        ref1 = atom.getReference()
        ref2 = atom.getReference()

        assert ref1 == ref2


class TestReportAtomAbstractMethods:
    """Tests for abstract methods that must be implemented."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that ReportAtom cannot be instantiated directly."""

        class IncompleteAtom(ReportAtom[MockSchema, MockMeta]):
            pass

        with pytest.raises(TypeError):
            IncompleteAtom()  # type: ignore

    def test_must_implement_render_table(self):
        """Test that renderTable must be implemented."""

        class NoRenderTable(ReportAtom[MockSchema, MockMeta]):
            def renderImage(self, output_dir: Path, force: bool = False) -> Path:
                return output_dir / "test.png"

            def renderSummary(self) -> str:
                return "summary"

        with pytest.raises(TypeError):
            NoRenderTable()  # type: ignore

    def test_must_implement_render_image(self):
        """Test that renderImage must be implemented."""

        class NoRenderImage(ReportAtom[MockSchema, MockMeta]):
            def renderTable(self) -> str:
                return "table"

            def renderSummary(self) -> str:
                return "summary"

        with pytest.raises(TypeError):
            NoRenderImage()  # type: ignore

    def test_must_implement_render_summary(self):
        """Test that renderSummary must be implemented."""

        class NoRenderSummary(ReportAtom[MockSchema, MockMeta]):
            def renderTable(self) -> str:
                return "table"

            def renderImage(self, output_dir: Path, force: bool = False) -> Path:
                return output_dir / "test.png"

        with pytest.raises(TypeError):
            NoRenderSummary()  # type: ignore
