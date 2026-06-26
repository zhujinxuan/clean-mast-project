"""Tests for vertical profile atoms — reporting domain.

Ported from tests/assessment/vertical_profile/test_vertical_profile_atoms.py.
Test logic preserved; only import paths updated.
"""

from pathlib import Path

import polars as pl
import pytest
from cleanmast.subdomains.reporting.subdomains.vertical_profile.model.report_meta import VerticalProfileAtomMeta
from cleanmast.subdomains.reporting.subdomains.vertical_profile.model.schemas import (
    VerticalProfileSchema,
    WindShearSchema,
)
from cleanmast.subdomains.reporting.subdomains.vertical_profile.model.wind_shear_exponent_atom import (
    SingleMastWindShearExponentAtom,
    create_single_mast_wind_shear_exponent_atom,
)
from typst_ir import TypstParagraph, TypstTable


@pytest.fixture
def sample_meta() -> VerticalProfileAtomMeta:
    return VerticalProfileAtomMeta(
        mast_name="TestMast",
        caption="Test caption",
    )


@pytest.fixture
def profile_df() -> pl.DataFrame:
    return pl.DataFrame({
        "height": [80.0, 100.0, 120.0],
        "interpolation_marker": [None, None, None],
        "wind_speed_mean": [7.5, 8.2, 8.8],
        "wind_speed_std": [1.5, 1.6, 1.7],
        "alpha": [0.15, 0.15, 0.15],
        "r_squared": [0.998, 0.998, 0.998],
    })


@pytest.fixture
def shear_df() -> pl.DataFrame:
    return pl.DataFrame({
        "from_height": [80.0, 80.0, 100.0],
        "to_height": [100.0, 120.0, 120.0],
        "alpha_mean": [0.15, 0.15, 0.15],
        "alpha_std": [0.03, 0.03, 0.03],
        "alpha_min": [0.08, 0.08, 0.08],
        "alpha_max": [0.25, 0.25, 0.25],
    })


@pytest.fixture
def wind_shear_atom(
    profile_df: pl.DataFrame,
    shear_df: pl.DataFrame,
    sample_meta: VerticalProfileAtomMeta,
) -> SingleMastWindShearExponentAtom:
    return create_single_mast_wind_shear_exponent_atom(
        profile_schema=VerticalProfileSchema,
        profile_df=profile_df,
        shear_schema=WindShearSchema,
        shear_df=shear_df,
        meta=sample_meta,
    )


class TestSingleMastWindShearExponentAtom:
    def test_render_table_combined_headers(
        self,
        wind_shear_atom: SingleMastWindShearExponentAtom,
    ) -> None:
        table = wind_shear_atom.renderTable()
        assert isinstance(table, TypstTable)
        assert "测风高度" in table.headers
        assert "平均风速(m/s)" in table.headers
        assert "80m" in table.headers
        assert "100m" in table.headers
        assert "120m" in table.headers

    def test_render_table_diagonal(
        self,
        wind_shear_atom: SingleMastWindShearExponentAtom,
    ) -> None:
        table = wind_shear_atom.renderTable()
        assert isinstance(table, TypstTable)
        for row in table.data:
            row_height = row[0]
            for col_header, cell in zip(table.headers[2:], row[2:], strict=True):
                if row_height == col_header:
                    assert cell == "◦"

    def test_render_table_symmetric(
        self,
        wind_shear_atom: SingleMastWindShearExponentAtom,
    ) -> None:
        table = wind_shear_atom.renderTable()
        assert isinstance(table, TypstTable)
        n = len(table.data)
        data_offset = 2
        for i in range(n):
            for j in range(n):
                if i != j:
                    assert table.data[i][j + data_offset] == table.data[j][i + data_offset]

    def test_render_image_creates_png(
        self,
        wind_shear_atom: SingleMastWindShearExponentAtom,
        tmp_path: Path,
    ) -> None:
        image_path = wind_shear_atom.renderImage(tmp_path)
        assert image_path is not None
        assert image_path.suffix == ".png"
        assert image_path.exists()

    def test_render_summary_single_sentence(
        self,
        wind_shear_atom: SingleMastWindShearExponentAtom,
    ) -> None:
        summary = wind_shear_atom.renderSummary()
        assert isinstance(summary, list)
        assert len(summary) == 1
        assert isinstance(summary[0], TypstParagraph)
        assert "根据 TestMast，得到总体高度的风切变指数为" in summary[0].text
        assert "0.150" in summary[0].text

    def test_resolve_table_caption_uses_meta(
        self,
        wind_shear_atom: SingleMastWindShearExponentAtom,
    ) -> None:
        caption = wind_shear_atom._resolve_table_caption()
        assert caption == "Test caption"
