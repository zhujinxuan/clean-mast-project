"""Tests for MultiMastRepYearCalibrationAtom and RepresentativeYearCalibrationSubsection."""

from pathlib import Path
from typing import Any

import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.entities.multi_masts.representative_year_calibration import (
    MultiMastRepYearCalibrationAtom,
)
from cleanmast.subdomains.assessment.domain.services.sections.representative_year_calibration import (
    RepresentativeYearCalibrationSubsection,
)
from cleanmast.subdomains.assessment.domain.types import (
    TypstParagraph,
    TypstSection,
    TypstTable,
)
from cleanmast.subdomains.assessment.domain.value_objects.collections.atom_collection import (
    AtomCollection,
)
from cleanmast.subdomains.assessment.domain.value_objects.multi_masts.report_meta import (
    MultiMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.multi_masts.schemas import (
    MultiMastRepYearCalibrationSchema,
)


@pytest.fixture
def sample_rep_year_calibration_df() -> pl.DataFrame:
    """Create sample representative year calibration DataFrame."""
    return pl.DataFrame({
        "year_range": ["1994-2023", "1994-2023"],
        "mast_name": ["M01", "M02"],
        "era5_name": ["ERA5-01", "ERA5-02"],
        "climatology_mean_ws": [6.1234, 5.9876],
        "rep_year_mean_ws": [6.3456, 5.7654],
        "anomaly_percent": [3.63, -3.71],
        "needs_correction": [True, False],
    })


@pytest.fixture
def rep_year_calibration_atom(
    sample_rep_year_calibration_df: pl.DataFrame,
) -> Any:
    """Create a MultiMastRepYearCalibrationAtom for testing."""
    meta = MultiMastMeta()
    return MultiMastRepYearCalibrationAtom.create(
        schema=MultiMastRepYearCalibrationSchema,
        df=sample_rep_year_calibration_df,
        meta=meta,
    )


@pytest.fixture
def rep_year_calibration_collection(
    rep_year_calibration_atom: Any,
) -> AtomCollection:
    """Create an AtomCollection with a MultiMastRepYearCalibrationAtom."""
    return AtomCollection.from_dict({
        "_all_masts": [rep_year_calibration_atom],
    })


class TestMultiMastRepYearCalibrationAtom:
    """Tests for MultiMastRepYearCalibrationAtom."""

    def test_create_succeeds(self, rep_year_calibration_atom: Any) -> None:
        """Test that .create() succeeds and returns a valid atom."""
        assert isinstance(rep_year_calibration_atom, MultiMastRepYearCalibrationAtom)
        assert hasattr(rep_year_calibration_atom, "df")
        assert hasattr(rep_year_calibration_atom, "meta")
        assert hasattr(rep_year_calibration_atom, "schema")

    def test_render_table_headers_in_exact_order(self, rep_year_calibration_atom: Any) -> None:
        """Test that renderTable returns correct headers in exact order."""
        result = rep_year_calibration_atom.renderTable()

        assert isinstance(result, TypstTable)
        expected_headers = [
            "测风代表年range",
            "mastname",
            "era5name",
            "30年气候平均基准ERA5风速",
            "测风代表年ERA5风速",
            "距平",
            "是否需要订正",
        ]
        assert result.headers == expected_headers

    def test_render_table_data_formatting(self, rep_year_calibration_atom: Any) -> None:
        """Test that renderTable data rows have correct formatting."""
        result = rep_year_calibration_atom.renderTable()

        assert isinstance(result, TypstTable)
        assert len(result.data) == 2

        row0 = result.data[0]
        assert "(m/s)" in row0[3]
        assert "(m/s)" in row0[4]
        assert "%" in row0[5]
        assert row0[6] == "是"

        row1 = result.data[1]
        assert "(m/s)" in row1[3]
        assert "(m/s)" in row1[4]
        assert "%" in row1[5]
        assert row1[6] == "否"

    def test_render_summary_returns_chinese_paragraphs(self, rep_year_calibration_atom: Any) -> None:
        """Test that renderSummary returns non-empty list of TypstParagraph with Chinese text."""
        result = rep_year_calibration_atom.renderSummary()

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TypstParagraph)
        assert len(result[0].text) > 0
        assert "代表年订正" in result[0].text

    def test_render_image_returns_empty_path(self, rep_year_calibration_atom: Any) -> None:
        """Test that renderImage returns empty Path (no image generation)."""
        output_dir = Path("/tmp")
        result = rep_year_calibration_atom.renderImage(output_dir)

        assert result == Path()


class TestRepresentativeYearCalibrationSubsection:
    """Tests for RepresentativeYearCalibrationSubsection."""

    def test_render_ir_returns_typst_section_with_correct_heading(
        self,
        rep_year_calibration_collection: AtomCollection,
        tmp_path: Path,
    ) -> None:
        """Test that render_ir returns TypstSection with correct heading text."""
        subsection = RepresentativeYearCalibrationSubsection(
            atoms=rep_year_calibration_collection
        )
        section_node = subsection.render_ir(tmp_path)

        assert isinstance(section_node, TypstSection)
        assert section_node.heading.text == "代表年订正"
