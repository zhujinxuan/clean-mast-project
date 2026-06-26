"""Tests for turbulence report atoms."""

from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_multi_atom import (
    SingleMastTurbulenceMultiHeightAtom,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_per_height_atom import (
    SingleMastTurbulencePerHeightAtom,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_summary_atom import (
    SingleMastTurbulenceSummaryAtom,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.value_objects.schemas import (
    TurbulenceSchema,
)
from typst_ir import TypstTable


@pytest.fixture
def sample_mast_meta() -> SingleMastMeta:
    return SingleMastMeta(mast_name="M01")


@pytest.fixture
def sample_turbulence_df() -> pl.DataFrame:
    return pl.DataFrame({
        "wind_speed_bin": [3, 5, 7, 9, 11, 13],
        "height": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
        "interpolation_marker": [None, None, None, None, None, None],
        "mean_ti": [0.18, 0.15, 0.12, 0.10, 0.09, 0.08],
        "std_ti": [0.03, 0.02, 0.02, 0.015, 0.01, 0.01],
        "representative_ti": [0.218, 0.176, 0.146, 0.119, 0.103, 0.093],
        "iec_category": ["B", "B", "A", "A", "A", "A"],
        "count": [42, 42, 42, 42, 42, 42],
    })


@pytest.fixture
def sample_turbulence_multi_height_df() -> pl.DataFrame:
    """Create a multi-height turbulence DataFrame for per-height table tests."""
    return pl.DataFrame({
        "wind_speed_bin": [3, 5, 7, 3, 5, 7],
        "height": [100.0, 100.0, 100.0, 130.0, 130.0, 130.0],
        "interpolation_marker": [None, None, None, None, None, None],
        "mean_ti": [0.18, 0.15, 0.12, 0.17, 0.14, 0.11],
        "std_ti": [0.03, 0.02, 0.02, 0.025, 0.02, 0.018],
        "representative_ti": [0.218, 0.176, 0.146, 0.202, 0.166, 0.133],
        "iec_category": ["B", "B", "A", "B", "B", "A"],
        "count": [42, 42, 42, 42, 42, 42],
    })


@pytest.fixture
def turbulence_per_height_atom(
    sample_turbulence_multi_height_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastTurbulencePerHeightAtom:
    return SingleMastTurbulencePerHeightAtom.create_with_height(
        schema=TurbulenceSchema,
        df=sample_turbulence_multi_height_df,
        meta=sample_mast_meta,
        height=100.0,
    )


class TestSingleMastTurbulencePerHeightAtom:
    """Tests for SingleMastTurbulencePerHeightAtom."""

    EXPECTED_HEADERS = [
        "风速区间 (m/s)",
        "平均湍流强度",
        "湍流强度标准差",
        "代表湍流强度(P90)",
        "IEC类别",
        "数据点数",
    ]

    def test_render_table_returns_single_table(
        self, turbulence_per_height_atom: SingleMastTurbulencePerHeightAtom
    ) -> None:
        """renderTable() should return a single TypstTable."""
        table = turbulence_per_height_atom.renderTable()

        assert isinstance(table, TypstTable)

    def test_render_table_headers(
        self, turbulence_per_height_atom: SingleMastTurbulencePerHeightAtom
    ) -> None:
        """Table should have the correct headers."""
        table = turbulence_per_height_atom.renderTable()

        assert table.headers == self.EXPECTED_HEADERS

    def test_render_table_caption_includes_height(
        self, turbulence_per_height_atom: SingleMastTurbulencePerHeightAtom
    ) -> None:
        """Table caption should include the height."""
        table = turbulence_per_height_atom.renderTable()

        assert "100m" in table.caption

    def test_render_summary_returns_empty_list(
        self, turbulence_per_height_atom: SingleMastTurbulencePerHeightAtom
    ) -> None:
        """renderSummary() should return an empty list."""
        summary = turbulence_per_height_atom.renderSummary()

        assert summary == []


@pytest.fixture
def multi_height_turbulence_df() -> pl.DataFrame:
    return pl.DataFrame({
        "wind_speed_bin": [3, 3, 3, 3, 5, 5, 5, 5],
        "height": [80.0, 100.0, 130.0, 150.0, 80.0, 100.0, 130.0, 150.0],
        "interpolation_marker": [None, None, None, None, None, None, None, None],
        "mean_ti": [0.20, 0.18, 0.14, 0.12, 0.19, 0.17, 0.13, 0.11],
        "std_ti": [0.04, 0.03, 0.02, 0.015, 0.04, 0.03, 0.02, 0.015],
        "representative_ti": [0.24, 0.218, 0.166, 0.139, 0.23, 0.208, 0.156, 0.129],
        "iec_category": ["B", "B", "A", "A", "B", "B", "A", "A"],
        "count": [42, 42, 42, 42, 42, 42, 42, 42],
    })


@pytest.fixture
def multi_height_turbulence_atom(
    multi_height_turbulence_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastTurbulenceMultiHeightAtom:
    return SingleMastTurbulenceMultiHeightAtom.create(
        schema=TurbulenceSchema,
        df=multi_height_turbulence_df,
        meta=sample_mast_meta,
    )


class TestSingleMastTurbulenceMultiHeightAtom:
    def test_render_image(
        self, multi_height_turbulence_atom: SingleMastTurbulenceMultiHeightAtom, tmp_path: Path
    ) -> None:
        image_path = multi_height_turbulence_atom.renderImage(tmp_path)

        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_image_uses_height_filter(
        self, multi_height_turbulence_atom: SingleMastTurbulenceMultiHeightAtom, tmp_path: Path
    ) -> None:
        with patch(
            "cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_multi_atom.select_interested_heights"
        ) as mock_filter:
            mock_filter.return_value = [130.0, 150.0]

            image_path = multi_height_turbulence_atom.renderImage(tmp_path, force=True)

            mock_filter.assert_called_once_with([80.0, 100.0, 130.0, 150.0])
            assert image_path.exists()
            assert image_path.suffix == ".png"
            assert image_path.stat().st_size > 0

    def test_render_image_fallback_to_top_heights(
        self, sample_mast_meta: SingleMastMeta, tmp_path: Path
    ) -> None:
        df = pl.DataFrame({
            "wind_speed_bin": [3, 3, 5, 5],
            "height": [50.0, 80.0, 50.0, 80.0],
            "interpolation_marker": [None, None, None, None],
            "mean_ti": [0.22, 0.20, 0.21, 0.19],
            "std_ti": [0.04, 0.03, 0.04, 0.03],
            "representative_ti": [0.26, 0.24, 0.25, 0.23],
            "iec_category": ["B", "B", "B", "B"],
            "count": [42, 42, 42, 42],
        })
        atom = SingleMastTurbulenceMultiHeightAtom.create(
            schema=TurbulenceSchema,
            df=df,
            meta=sample_mast_meta,
        )

        with patch(
            "cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_multi_atom.select_interested_heights"
        ) as mock_filter:
            mock_filter.return_value = [50.0, 80.0]

            image_path = atom.renderImage(tmp_path, force=True)

            mock_filter.assert_called_once_with([50.0, 80.0])
            assert image_path.exists()
            assert image_path.suffix == ".png"
            assert image_path.stat().st_size > 0


@pytest.fixture
def sample_turbulence_summary_df() -> pl.DataFrame:
    """Create sample turbulence DataFrame for summary atom testing.

    Includes two heights (100m and 140m) with wind speed bins covering
    the >3, 9.5-10.5, and 14.5-16.5 m/s ranges needed by renderTable
    and renderSummary.
    """
    return pl.DataFrame({
        "wind_speed_bin": [3, 5, 9, 10, 14, 15, 16,
                           3, 5, 9, 10, 14, 15, 16],
        "height": [100.0] * 7 + [140.0] * 7,
        "interpolation_marker": [None] * 7 + ["外推"] * 7,
        "mean_ti": [0.18, 0.15, 0.10, 0.09, 0.08, 0.075, 0.07,
                    0.17, 0.14, 0.09, 0.085, 0.075, 0.07, 0.065],
        "std_ti": [0.03, 0.02, 0.015, 0.014, 0.01, 0.009, 0.008,
                   0.025, 0.018, 0.013, 0.012, 0.009, 0.008, 0.007],
        "representative_ti": [0.218, 0.176, 0.119, 0.108, 0.093, 0.087, 0.080,
                              0.202, 0.163, 0.107, 0.100, 0.087, 0.080, 0.074],
        "iec_category": ["B", "B", "A", "A", "A", "A", "A",
                        "B", "B", "A", "A", "A", "A", "A"],
        "count": [42, 42, 42, 42, 42, 42, 42, 42, 42, 42, 42, 42, 42, 42],
    })


@pytest.fixture
def turbulence_summary_atom(
    sample_turbulence_summary_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastTurbulenceSummaryAtom:
    return SingleMastTurbulenceSummaryAtom.create(
        schema=TurbulenceSchema,
        df=sample_turbulence_summary_df,
        meta=sample_mast_meta,
    )


class TestSingleMastTurbulenceSummaryAtom:
    """Tests for SingleMastTurbulenceSummaryAtom table and summary rendering."""

    def test_render_table(self, turbulence_summary_atom: SingleMastTurbulenceSummaryAtom) -> None:
        """Summary table should show three rows per interested height with correct headers."""
        table = turbulence_summary_atom.renderTable()

        assert isinstance(table, TypstTable)
        assert table.headers == [
            "高度(m)",
            "风速范围",
            "平均湍流强度",
            "代表湍流强度(P90)",
            "湍流强度标准差",
        ]
        assert table.caption == "M01 湍流强度统计表"

        # 140m is in range [120, 160]; 100m is not. With min_count=2,
        # select_interested_heights falls back to top 2 heights, so both appear.
        assert len(table.data) == 6
        assert table.data[0][0] == "100m"
        assert table.data[0][1] == ">3 m/s"
        assert table.data[1][1] == "14.5-16.5 m/s"
        assert table.data[2][1] == "9.5-10.5 m/s"
        assert table.data[3][0] == "140m 外推"
        assert table.data[3][1] == ">3 m/s"
        assert table.data[4][1] == "14.5-16.5 m/s"
        assert table.data[5][1] == "9.5-10.5 m/s"

    def test_render_table_no_data_range(self, sample_mast_meta: SingleMastMeta) -> None:
        """Missing data for a wind speed range should show '-'."""
        df = pl.DataFrame({
            "wind_speed_bin": [3, 5],
            "height": [100.0, 100.0],
            "interpolation_marker": [None, None],
            "mean_ti": [0.18, 0.15],
            "std_ti": [0.03, 0.02],
            "representative_ti": [0.218, 0.176],
            "iec_category": ["B", "B"],
            "count": [42, 42],
        })
        atom = SingleMastTurbulenceSummaryAtom.create(
            schema=TurbulenceSchema, df=df, meta=sample_mast_meta
        )
        table = atom.renderTable()

        # >3 m/s has data (5 > 3), 14.5-16.5 and 9.5-10.5 have no data
        assert table.data[0][2] != "-"
        assert table.data[1][2] == "-"
        assert table.data[1][3] == "-"
        assert table.data[1][4] == "-"
        assert table.data[2][2] == "-"
        assert table.data[2][3] == "-"
        assert table.data[2][4] == "-"

    def test_render_summary(self, turbulence_summary_atom: SingleMastTurbulenceSummaryAtom) -> None:
        """Summary should list per-height 15m/s rep TI and the closest IEC category."""
        summary = turbulence_summary_atom.renderSummary()

        assert len(summary) == 1
        text = summary[0].text

        assert "M01" in text
        assert "100m" in text
        assert "140m 外推" in text

        # 100m 14.5-16.5 rep TI mean = (0.093 + 0.087 + 0.080) / 3 ≈ 0.087
        # 140m 14.5-16.5 rep TI mean = (0.087 + 0.080 + 0.074) / 3 ≈ 0.080
        assert "0.087" in text
        assert "0.080" in text

        # Mean rep TI ≈ 0.0835; closest IEC category at 15 m/s is C
        assert "IEC C 类" in text

    def test_render_summary_fallback(self, sample_mast_meta: SingleMastMeta) -> None:
        """Summary should fallback when no 14.5-16.5 m/s data exists."""
        df = pl.DataFrame({
            "wind_speed_bin": [3, 5, 7],
            "height": [100.0, 100.0, 100.0],
            "interpolation_marker": [None, None, None],
            "mean_ti": [0.18, 0.15, 0.12],
            "std_ti": [0.03, 0.02, 0.02],
            "representative_ti": [0.218, 0.176, 0.146],
            "iec_category": ["B", "B", "A"],
            "count": [42, 42, 42],
        })
        atom = SingleMastTurbulenceSummaryAtom.create(
            schema=TurbulenceSchema, df=df, meta=sample_mast_meta
        )
        summary = atom.renderSummary()

        assert len(summary) == 1
        assert "暂无15m/s附近风速区间的有效湍流强度数据" in summary[0].text
