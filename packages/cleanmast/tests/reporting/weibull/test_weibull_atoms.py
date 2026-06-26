"""Tests for the combined Weibull report atom — reporting domain.

Ported from tests/assessment/weibull/test_weibull_atoms.py.
Test logic, inputs, expected values, assertions preserved exactly.
"""

from pathlib import Path

import polars as pl
import pytest
from cleanmast.subdomains.reporting.subdomains.weibull.model.report_meta import (
    WeibullAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.weibull.model.schemas import (
    WeibullSchema,
)
from cleanmast.subdomains.reporting.subdomains.weibull.model.weibull_atom import (
    WeibullSubgridAtom,
)
from typst_ir import TypstParagraph, TypstTable


@pytest.fixture
def sample_mast_meta() -> WeibullAtomMeta:
    return WeibullAtomMeta(mast_name="M01")


@pytest.fixture
def sample_weibull_subgrid_df() -> pl.DataFrame:
    rows = []
    for bc in [0.5, 1.5, 2.5]:
        rows.append(
            {
                "height": 100.0,
                "bin_center": bc,
                "observed_density": 0.02,
                "fitted_density": 0.025,
                "shape_k": 1.8,
                "scale_c": 7.0,
                "interpolation_marker": None,
            }
        )
    for bc in [0.5, 1.5, 2.5]:
        rows.append(
            {
                "height": 130.0,
                "bin_center": bc,
                "observed_density": 0.03,
                "fitted_density": 0.028,
                "shape_k": 2.1,
                "scale_c": 8.5,
                "interpolation_marker": "外推",
            }
        )
    for bc in [0.5, 1.5, 2.5]:
        rows.append(
            {
                "height": 150.0,
                "bin_center": bc,
                "observed_density": 0.025,
                "fitted_density": 0.024,
                "shape_k": 2.3,
                "scale_c": 9.2,
                "interpolation_marker": None,
            }
        )
    for bc in [0.5, 1.5, 2.5]:
        rows.append(
            {
                "height": 170.0,
                "bin_center": bc,
                "observed_density": 0.015,
                "fitted_density": 0.018,
                "shape_k": 2.0,
                "scale_c": 8.0,
                "interpolation_marker": "外推",
            }
        )
    return pl.DataFrame(rows)


@pytest.fixture
def weibull_subgrid_atom(
    sample_weibull_subgrid_df: pl.DataFrame,
    sample_mast_meta: WeibullAtomMeta,
) -> WeibullSubgridAtom:
    return WeibullSubgridAtom.create(
        schema=WeibullSchema,
        df=sample_weibull_subgrid_df,
        meta=sample_mast_meta,
    )


class TestWeibullSubgridAtom:
    def test_render_table_filters_heights(
        self, weibull_subgrid_atom: WeibullSubgridAtom
    ) -> None:
        table = weibull_subgrid_atom.renderTable()

        assert isinstance(table, TypstTable)
        table_text = str(table.data)
        assert "130" in table_text
        assert "150" in table_text
        assert "100" not in table_text
        assert "170" not in table_text

    def test_render_table_columns(
        self, weibull_subgrid_atom: WeibullSubgridAtom
    ) -> None:
        table = weibull_subgrid_atom.renderTable()

        assert isinstance(table, TypstTable)
        headers = [str(h) for h in table.headers]
        assert any("高度" in h for h in headers)
        assert any("形状参数k" in h for h in headers)
        assert any("尺度参数c" in h for h in headers)

    def test_render_table_values_match_sample_data(
        self, weibull_subgrid_atom: WeibullSubgridAtom
    ) -> None:
        table = weibull_subgrid_atom.renderTable()

        assert isinstance(table, TypstTable)
        table_text = str(table.data)
        assert "2.10" in table_text or "2.1" in table_text
        assert "8.50" in table_text or "8.5" in table_text
        assert "2.30" in table_text or "2.3" in table_text
        assert "9.20" in table_text or "9.2" in table_text

    def test_render_image_returns_png_path(
        self, weibull_subgrid_atom: WeibullSubgridAtom, tmp_path: Path
    ) -> None:
        image_path = weibull_subgrid_atom.renderImage(tmp_path)

        assert isinstance(image_path, Path)
        assert image_path.suffix == ".png"

    def test_render_image_file_exists_and_non_empty(
        self, weibull_subgrid_atom: WeibullSubgridAtom, tmp_path: Path
    ) -> None:
        image_path = weibull_subgrid_atom.renderImage(tmp_path)

        assert image_path.exists()
        assert image_path.stat().st_size > 0

    def test_render_summary(
        self, weibull_subgrid_atom: WeibullSubgridAtom
    ) -> None:
        summary = weibull_subgrid_atom.renderSummary()

        assert isinstance(summary, list)
        assert len(summary) > 0
        assert isinstance(summary[0], TypstParagraph)
        assert any("\u4e00" <= char <= "\u9fff" for char in summary[0].text)

    def test_content_hash_consistency(
        self, weibull_subgrid_atom: WeibullSubgridAtom
    ) -> None:
        hash1 = weibull_subgrid_atom.get_or_compute_df_hashkey()
        hash2 = weibull_subgrid_atom.get_or_compute_df_hashkey()

        assert hash1 == hash2
        assert "WeibullSubgridAtom_" in hash1

    def test_default_captions(
        self, weibull_subgrid_atom: WeibullSubgridAtom
    ) -> None:
        assert weibull_subgrid_atom.default_image_caption is not None
        assert "M01" in weibull_subgrid_atom.default_image_caption
        assert weibull_subgrid_atom.default_table_caption is not None
        assert "M01" in weibull_subgrid_atom.default_table_caption
