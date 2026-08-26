"""Tests for turbulence report atoms.

Adapted from assessment tests. Key changes:
- Import from reporting.subdomains.turbulence.model instead of assessment
- TurbulenceAtomMeta from reporting turbulence (frozen)
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import pytest
from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
from cleanmast.subdomains.reporting.model.analysis_input import SingleMastAnalysisInput
from cleanmast.subdomains.reporting.model.analysis_parameters import AnalysisParameters
from cleanmast.subdomains.reporting.subdomains.turbulence.model.report_meta import (
    TurbulenceAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.model.schemas import (
    TurbulenceSchema,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.model.turbulence_multi_atom import (
    SingleMastTurbulenceMultiHeightAtom,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.model.turbulence_per_height_atom import (
    SingleMastTurbulencePerHeightAtom,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.model.turbulence_summary_atom import (
    SingleMastTurbulenceSummaryAtom,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.section import TurbulenceSection
from typst_ir import TypstTable


@pytest.fixture
def sample_mast_meta() -> TurbulenceAtomMeta:
    return TurbulenceAtomMeta(mast_name="M01", interested_heights=[100.0, 140.0])


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
    sample_mast_meta: TurbulenceAtomMeta,
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
    sample_mast_meta: TurbulenceAtomMeta,
) -> SingleMastTurbulenceMultiHeightAtom:
    return SingleMastTurbulenceMultiHeightAtom.create(
        schema=TurbulenceSchema,
        df=multi_height_turbulence_df,
        meta=sample_mast_meta,
    )


class TestSingleMastTurbulenceMultiHeightAtom:
    def test_render_image(
        self,
        multi_height_turbulence_atom: SingleMastTurbulenceMultiHeightAtom,
        tmp_path: Path,
    ) -> None:
        image_path = multi_height_turbulence_atom.renderImage(tmp_path)

        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0


@pytest.fixture
def sample_turbulence_summary_df() -> pl.DataFrame:
    """Create sample turbulence DataFrame for summary atom testing."""
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
    sample_mast_meta: TurbulenceAtomMeta,
) -> SingleMastTurbulenceSummaryAtom:
    return SingleMastTurbulenceSummaryAtom.create(
        schema=TurbulenceSchema,
        df=sample_turbulence_summary_df,
        meta=sample_mast_meta,
    )


class TestSingleMastTurbulenceSummaryAtom:
    """Tests for SingleMastTurbulenceSummaryAtom table and summary rendering."""

    def test_render_table(
        self, turbulence_summary_atom: SingleMastTurbulenceSummaryAtom
    ) -> None:
        """Summary table shows one 14.5-15.5 m/s row per height with 数据点数."""
        table = turbulence_summary_atom.renderTable()

        assert isinstance(table, TypstTable)
        assert table.headers == [
            "高度(m)",
            "风速范围",
            "平均湍流强度",
            "代表湍流强度(P90)",
            "湍流强度标准差",
            "数据点数",
        ]
        assert table.caption == "M01 湍流强度统计表"

        # One row per interested height; band 14.5-15.5 = bins 14 and 15.
        assert len(table.data) == 2
        assert table.data[0][0] == "100m"
        assert table.data[1][0] == "140m(外推)"
        for row in table.data:
            assert row[1] == "14.5-15.5 m/s"
        # 数据点数 sums the counts of bins 14 and 15.
        assert table.data[0][5] == "84"
        assert table.data[1][5] == "84"

    def test_render_table_no_data_range(
        self, sample_mast_meta: TurbulenceAtomMeta
    ) -> None:
        """Missing data for the 14.5-15.5 band should show '-'."""
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

        # One row per interested height; no bins 14/15 anywhere → all "-".
        assert len(table.data) == 2
        for row in table.data:
            assert row[1] == "14.5-15.5 m/s"
            assert row[2:] == ["-", "-", "-", "-"]

    def test_render_summary(
        self, turbulence_summary_atom: SingleMastTurbulenceSummaryAtom
    ) -> None:
        """Summary lists per-height 14.5-15.5 band rep TI and the IEC category."""
        summary = turbulence_summary_atom.renderSummary()

        assert len(summary) == 1
        text = summary[0].text

        assert "M01" in text
        assert "100m" in text
        assert "140m(外推)" in text

        # 100m 14.5-15.5 rep TI mean = (0.093 + 0.087) / 2 = 0.090
        # 140m 14.5-15.5 rep TI mean = (0.087 + 0.080) / 2 ≈ 0.083
        assert "0.090" in text
        assert "0.083" in text

        # Mean rep TI ≈ 0.0868; below the C reference curve at 15 m/s → C
        assert "IEC C 类" in text

    def test_render_summary_band_membership_classification(
        self, sample_mast_meta: TurbulenceAtomMeta
    ) -> None:
        """Regression: rep TI between C and B reference curves classifies B.

        The pre-fix inline threshold chain required exceeding the B curve for
        a B verdict, reporting C where per-bin tables reported B. The sentence
        must use the shared band-membership classifier.
        """
        df = pl.DataFrame({
            "wind_speed_bin": [14, 15],
            "height": [100.0, 100.0],
            "interpolation_marker": [None, None],
            "mean_ti": [0.12, 0.12],
            "std_ti": [0.02, 0.02],
            # 0.150 is above the C curve (0.1348) but below the B curve
            # (0.1573) at 15 m/s → band membership ⇒ B.
            "representative_ti": [0.150, 0.150],
            "iec_category": ["B", "B"],
            "count": [100, 100],
        })
        atom = SingleMastTurbulenceSummaryAtom.create(
            schema=TurbulenceSchema, df=df, meta=sample_mast_meta
        )
        summary = atom.renderSummary()

        assert len(summary) == 1
        assert "IEC B 类" in summary[0].text

    def test_render_summary_fallback(
        self, sample_mast_meta: TurbulenceAtomMeta
    ) -> None:
        """Summary should fallback when no 14.5-15.5 m/s data exists."""
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


def _make_turbulence_time_series(
    mast_name: str,
    heights: list[float],
    seed: int,
) -> TimeSeriesData:
    """Build a deterministic TimeSeriesData for turbulence analysis."""
    rng = np.random.default_rng(seed)
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]

    data: dict[str, Any] = {"timestamp": timestamps}
    sensors: list[SensorColumn] = []

    for height in heights:
        base_speed = 8.0 + rng.uniform(-1.0, 1.0)
        wind_speeds = np.maximum(
            base_speed
            + 3.0 * np.sin(np.linspace(0, 4 * np.pi, 1000))
            + rng.normal(0.0, 0.5, 1000),
            0.5,
        )
        avg_col = f"WS_{int(height)}m_avg"
        sd_col = f"WS_{int(height)}m_sd"
        data[avg_col] = wind_speeds
        data[sd_col] = wind_speeds * 0.15
        sensors.append(
            SensorColumn(
                column_name=avg_col,
                sensor_type="WindSpeed",
                sensor_direction="",
                height=float(height),
                stat_type="avg",
                unit="m/s",
            )
        )
        sensors.append(
            SensorColumn(
                column_name=sd_col,
                sensor_type="WindSpeed",
                sensor_direction="",
                height=float(height),
                stat_type="sd",
                unit="m/s",
            )
        )

    return TimeSeriesData(df=pl.DataFrame(data), sensors=sensors)


class TestTurbulenceSectionMultiMast:
    """Integration tests for TurbulenceSection across multiple masts."""

    def test_per_height_atoms_isolated_by_mast(self) -> None:
        """Each mast's per-height atoms must only contain that mast's heights."""
        mast1 = _make_turbulence_time_series("Mast1", [100, 130], seed=1)
        mast2 = _make_turbulence_time_series("Mast2", [120, 150], seed=2)

        section = TurbulenceSection.from_time_series(
            [
                (mast1, "Mast1"),
                (mast2, "Mast2"),
            ],
            mast_turbulence_heights={
                "Mast1": [100.0, 130.0],
                "Mast2": [120.0, 150.0],
            },
        )

        per_height_atoms = [
            atom
            for atom in section.atoms
            if isinstance(atom, SingleMastTurbulencePerHeightAtom)
        ]

        # Each mast gets one summary, one multi-height, and per-height atoms.
        assert len(per_height_atoms) == 4

        expected_heights_by_mast = {
            "Mast1": {100.0, 130.0},
            "Mast2": {120.0, 150.0},
        }

        for atom in per_height_atoms:
            mast = atom.meta.mast_name
            atom_heights = set(atom.df["height"].unique().to_list())
            assert atom_heights <= expected_heights_by_mast[mast]
            assert atom.height in expected_heights_by_mast[mast]

    def test_summary_and_multi_height_atoms_isolated_by_mast(self) -> None:
        """Summary and multi-height atoms must only span their own mast's heights."""
        mast1 = _make_turbulence_time_series("Mast1", [100, 130], seed=3)
        mast2 = _make_turbulence_time_series("Mast2", [120, 150], seed=4)

        section = TurbulenceSection.from_time_series(
            [
                (mast1, "Mast1"),
                (mast2, "Mast2"),
            ],
            mast_turbulence_heights={
                "Mast1": [100.0, 130.0],
                "Mast2": [120.0, 150.0],
            },
        )

        expected_heights_by_mast = {
            "Mast1": {100.0, 130.0},
            "Mast2": {120.0, 150.0},
        }

        for atom in section.atoms:
            mast = atom.meta.mast_name
            atom_heights = set(atom.df["height"].unique().to_list())
            assert atom_heights <= expected_heights_by_mast[mast], (
                f"{type(atom).__name__} for {mast} contains heights {atom_heights}"
            )

    def test_empty_input_returns_empty_section(self) -> None:
        """Passing no masts should produce an empty atom list."""
        section = TurbulenceSection.from_time_series([], mast_turbulence_heights={})
        assert list(section.atoms) == []

    def test_from_inputs_raises_on_empty_turbulence_heights(self) -> None:
        """from_inputs must raise ValueError when turbulence_heights is empty."""
        mast = _make_turbulence_time_series("Mast1", [100.0], seed=1)
        parameters = AnalysisParameters(
            air_density=1.225,
            extreme_wind_10min_heights=[],
            extreme_wind_3s_heights=[],
            extreme_wind_gust_factors=[],
            turbulence_heights=[],
        )
        item = SingleMastAnalysisInput(
            time_series=mast,
            parameters=parameters,
            mast_name="Mast1",
        )
        with pytest.raises(ValueError, match="turbulence_heights"):
            TurbulenceSection.from_inputs([item])

    def test_from_inputs_accepts_nonempty_turbulence_heights(self) -> None:
        """from_inputs must not raise when turbulence_heights is non-empty."""
        mast = _make_turbulence_time_series("Mast1", [100.0], seed=1)
        parameters = AnalysisParameters(
            air_density=1.225,
            extreme_wind_10min_heights=[],
            extreme_wind_3s_heights=[],
            extreme_wind_gust_factors=[],
            turbulence_heights=[100.0, 140.0],
        )
        item = SingleMastAnalysisInput(
            time_series=mast,
            parameters=parameters,
            mast_name="Mast1",
        )
        section = TurbulenceSection.from_inputs([item])
        assert section._mast_names == ["Mast1"]
