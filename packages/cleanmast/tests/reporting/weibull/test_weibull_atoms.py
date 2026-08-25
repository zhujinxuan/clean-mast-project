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
    def test_render_table_includes_all_heights(
        self, weibull_subgrid_atom: WeibullSubgridAtom
    ) -> None:
        table = weibull_subgrid_atom.renderTable()

        assert isinstance(table, TypstTable)
        table_text = str(table.data)
        assert "130" in table_text
        assert "150" in table_text

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


class TestWeibullSectionGuard:
    """Tests for the from_inputs guard on empty weibull_heights."""

    def test_from_inputs_raises_on_empty_weibull_heights(self) -> None:
        """WeibullSection.from_inputs raises ValueError when weibull_heights is empty."""
        from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
        from cleanmast.subdomains.reporting.model.analysis_input import (
            SingleMastAnalysisInput,
        )
        from cleanmast.subdomains.reporting.model.analysis_parameters import (
            AnalysisParameters,
        )
        from cleanmast.subdomains.reporting.subdomains.weibull.section import (
            WeibullSection,
        )

        sensors = [
            SensorColumn(
                column_name="WindSpeed_100m_avg [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]
        ts_data = TimeSeriesData(
            df=pl.DataFrame({"WindSpeed_100m_avg [m/s]": [5.0]}),
            sensors=sensors,
        )

        item = SingleMastAnalysisInput(
            time_series=ts_data,
            parameters=AnalysisParameters(
                air_density=1.225,
                extreme_wind_10min_heights=[],
                extreme_wind_3s_heights=[],
                extreme_wind_gust_factors=[],
                weibull_heights=[],  # empty — should trigger guard
            ),
            mast_name="M01",
        )

        with pytest.raises(ValueError, match="weibull_heights"):
            WeibullSection.from_inputs([item])

    def test_from_inputs_succeeds_with_nonempty_weibull_heights(self) -> None:
        """WeibullSection.from_inputs succeeds when weibull_heights is populated."""
        from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
        from cleanmast.subdomains.reporting.model.analysis_input import (
            SingleMastAnalysisInput,
        )
        from cleanmast.subdomains.reporting.model.analysis_parameters import (
            AnalysisParameters,
        )
        from cleanmast.subdomains.reporting.subdomains.weibull.section import (
            WeibullSection,
        )

        sensors = [
            SensorColumn(
                column_name="WindSpeed_130m_avg [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=130.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WindSpeed_150m_avg [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=150.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]
        ts_data = TimeSeriesData(
            df=pl.DataFrame(
                {
                    "WindSpeed_130m_avg [m/s]": [5.0, 6.0, 7.0, 8.0, 9.0, 5.5, 6.5, 7.5, 8.5, 6.0, 7.0],
                    "WindSpeed_150m_avg [m/s]": [5.5, 6.5, 7.5, 8.5, 9.5, 6.0, 7.0, 8.0, 9.0, 6.5, 7.5],
                }
            ),
            sensors=sensors,
        )

        item = SingleMastAnalysisInput(
            time_series=ts_data,
            parameters=AnalysisParameters(
                air_density=1.225,
                extreme_wind_10min_heights=[],
                extreme_wind_3s_heights=[],
                extreme_wind_gust_factors=[],
                weibull_heights=[130.0, 150.0],
            ),
            mast_name="M01",
        )

        section = WeibullSection.from_inputs([item])
        assert section is not None
        assert len(section.atoms) >= 1
