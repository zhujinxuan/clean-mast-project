"""Tests for ReportAtom base class."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, overload

import dataframely as dy
import polars as pl
import pytest
from cleanmast.subdomains.assessment.shared.protocols.report_atom import (
    ReportAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.entities.monthly_pattern_atom import (
    SingleMastMonthlyPatternAtom,
)
from cleanmast.subdomains.assessment.shared.ir_types import (
    TypstFigure,
    TypstParagraph,
    TypstTable,
)
from cleanmast.subdomains.assessment.domain.value_objects import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.value_objects.schemas import (
    TemporalPatternSchema,
)
from typing_extensions import override


class MockSchema:
    """Mock schema for testing."""

    @overload
    @classmethod
    def validate(
        cls,
        df: pl.DataFrame | pl.LazyFrame,
        /,
        *,
        cast: bool = False,
        eager: Literal[True] = True,
    ) -> dy.DataFrame: ...

    @overload
    @classmethod
    def validate(
        cls,
        df: pl.DataFrame | pl.LazyFrame,
        /,
        *,
        cast: bool = False,
        eager: Literal[False],
    ) -> dy.LazyFrame: ...

    @overload
    @classmethod
    def validate(
        cls,
        df: pl.DataFrame | pl.LazyFrame,
        /,
        *,
        cast: bool = False,
        eager: bool,
    ) -> dy.DataFrame | dy.LazyFrame: ...

    @classmethod
    def validate(
        cls,
        df: pl.DataFrame | pl.LazyFrame,
        /,
        *,
        cast: bool = False,
        eager: bool = True,
    ) -> dy.DataFrame | dy.LazyFrame:
        """Pass-through validation for testing."""
        return df  # type: ignore[return-value]


@dataclass
class MockMeta:
    """Mock metadata for testing."""

    caption: str | None = "Test Caption"
    width: str = "80%"


@dataclass
class ConcreteAtom(ReportAtom[MockSchema, MockMeta]):
    """Concrete implementation of ReportAtom for testing."""

    @override
    def renderTable(self) -> TypstTable | None:
        return TypstTable(headers=["Test"], data=[["test"]])

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return output_dir / "test.png"

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return [TypstParagraph(text="Test summary")]


class TestReportAtomCreate:
    """Tests for ReportAtom.create factory method."""

    def test_create_validates_dataframe(self):
        """Test that create validates the DataFrame with the schema."""
        df = pl.DataFrame({
            "timestamp": [datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 1, 1, 0)],
            "hour": [0, 1],
            "month": [1, 1],
            "wind_speed": [5.0, 6.0],
            "wind_power": [100.0, 120.0],
            "height": [100.0, 100.0],
            "mean_speed": [5.5, 5.5],
            "mean_power": [110.0, 110.0],
            "interpolation_marker": [None, None],
        })
        meta = SingleMastMeta(mast_name="Test")

        atom = SingleMastMonthlyPatternAtom.create(
            schema=TemporalPatternSchema,
            df=df,
            meta=meta,
        )

        assert atom.df is not None
        assert atom.schema == TemporalPatternSchema
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

        assert result is not None
        assert isinstance(result, TypstFigure)
        assert result.content == "images/test.png"
        assert result.caption == "Test Figure"

    def test_render_image_typst_includes_label(self, tmp_path: Path):
        """Test that renderImageTypst includes proper label reference."""
        df = pl.DataFrame({"col": [1, 2, 3]})
        meta = MockMeta()

        atom = ConcreteAtom.create(schema=MockSchema, df=df, meta=meta)
        output_dir = tmp_path / "images"
        output_dir.mkdir()

        result = atom.renderImageTypst(output_dir)
        hashkey = atom.get_or_compute_df_hashkey()
        reference = atom.getReference()

        assert result is not None
        assert result.content == "images/test.png"
        assert reference == f"@fig-{hashkey}"


class TestReportAtomCaptionProperties:
    """Tests for default caption properties."""

    def test_default_image_caption_is_none(self):
        """Test that default_image_caption returns None by default."""
        df = pl.DataFrame({"col": [1, 2, 3]})
        meta = MockMeta()

        atom = ConcreteAtom.create(schema=MockSchema, df=df, meta=meta)

        assert hasattr(atom, "default_image_caption")
        assert atom.default_image_caption is None

    def test_default_table_caption_is_none(self):
        """Test that default_table_caption returns None by default."""
        df = pl.DataFrame({"col": [1, 2, 3]})
        meta = MockMeta()

        atom = ConcreteAtom.create(schema=MockSchema, df=df, meta=meta)

        assert hasattr(atom, "default_table_caption")
        assert atom.default_table_caption is None


@dataclass
class ConcreteAtomWithDefaultCaption(ReportAtom[MockSchema, MockMeta]):
    """Concrete atom with default captions for testing."""

    @property
    def default_image_caption(self) -> str | None:
        return "Default Image Caption"

    @property
    def default_table_caption(self) -> str | None:
        return "Default Table Caption"

    @override
    def renderTable(self) -> TypstTable | None:
        return TypstTable(headers=["Test"], data=[["test"]])

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return output_dir / "test.png"

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return [TypstParagraph(text="Test summary")]


class TestReportAtomCaptionResolution:
    """Tests for caption resolution chain."""

    def test_meta_caption_overrides_default(self, tmp_path: Path):
        """When meta.caption is set, it takes precedence."""
        df = pl.DataFrame({"col": [1, 2, 3]})
        meta = MockMeta(caption="Meta Caption")

        atom = ConcreteAtomWithDefaultCaption.create(schema=MockSchema, df=df, meta=meta)
        output_dir = tmp_path / "images"
        output_dir.mkdir()

        result = atom.renderImageTypst(output_dir)

        assert result is not None
        assert result.caption == "Meta Caption"

    def test_default_image_caption_used_when_meta_is_none(self, tmp_path: Path):
        """When meta.caption is None, fall back to default_image_caption."""
        df = pl.DataFrame({"col": [1, 2, 3]})
        meta = MockMeta(caption=None)

        atom = ConcreteAtomWithDefaultCaption.create(schema=MockSchema, df=df, meta=meta)
        output_dir = tmp_path / "images"
        output_dir.mkdir()

        result = atom.renderImageTypst(output_dir)

        assert result is not None
        assert result.caption == "Default Image Caption"

    def test_falls_back_to_figure_when_both_none(self, tmp_path: Path):
        """When both meta.caption and default_image_caption are None, fall back to 'Figure'."""
        df = pl.DataFrame({"col": [1, 2, 3]})
        meta = MockMeta(caption=None)

        atom = ConcreteAtom.create(schema=MockSchema, df=df, meta=meta)
        output_dir = tmp_path / "images"
        output_dir.mkdir()

        result = atom.renderImageTypst(output_dir)

        assert result is not None
        assert result.caption == "Figure"


@dataclass
class NoImageAtom(ReportAtom[MockSchema, MockMeta]):
    """Atom that generates no actual image file."""

    @override
    def renderTable(self) -> TypstTable | None:
        return TypstTable(headers=["Test"], data=[["test"]])

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        return output_dir

    @override
    def renderSummary(self) -> list[TypstParagraph]:
        return [TypstParagraph(text="No image")]


class TestReportAtomNoImage:
    """Tests for atoms that do not produce images."""

    def test_render_image_typst_returns_none_when_no_image(self, tmp_path: Path):
        """Test that renderImageTypst returns None when renderImage returns output_dir."""
        df = pl.DataFrame({"col": [1, 2, 3]})
        meta = MockMeta()

        atom = NoImageAtom.create(schema=MockSchema, df=df, meta=meta)
        output_dir = tmp_path / "images"
        output_dir.mkdir()

        result = atom.renderImageTypst(output_dir)

        assert result is None


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

            def renderSummary(self) -> list[TypstParagraph]:
                return [TypstParagraph(text="summary")]

        with pytest.raises(TypeError):
            NoRenderTable()  # type: ignore

    def test_must_implement_render_image(self):
        """Test that renderImage must be implemented."""

        class NoRenderImage(ReportAtom[MockSchema, MockMeta]):
            def renderTable(self) -> TypstTable | None:
                return TypstTable(headers=["Test"], data=[["test"]])

            def renderSummary(self) -> list[TypstParagraph]:
                return [TypstParagraph(text="summary")]

        with pytest.raises(TypeError):
            NoRenderImage()  # type: ignore

    def test_must_implement_render_summary(self):
        """Test that renderSummary must be implemented."""

        class NoRenderSummary(ReportAtom[MockSchema, MockMeta]):
            def renderTable(self) -> TypstTable | None:
                return TypstTable(headers=["Test"], data=[["test"]])

            def renderImage(self, output_dir: Path, force: bool = False) -> Path:
                return output_dir / "test.png"

        with pytest.raises(TypeError):
            NoRenderSummary()  # type: ignore
