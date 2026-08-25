"""Tests for WindRoseSection config-driven heights — reporting domain.

Covers the wind_rose_heights contract: empty list hard-fails, and the
computed frame is filtered to the configured heights before atoms are built.
"""

import polars as pl
import pytest
from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
from cleanmast.subdomains.reporting.model.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.reporting.model.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.section import (
    WindRoseSection,
)


def _paired_time_series(heights: list[float]) -> TimeSeriesData:
    """TimeSeriesData with exact WS avg + WD avg pairs at each height."""
    n = 8
    data = {"timestamp": pl.Series(
        [f"2024-01-{i:02d}T00:00:00" for i in range(1, n + 1)]
    ).str.to_datetime()}
    sensors: list[SensorColumn] = []
    for height in heights:
        ws_col = f"WS_{int(height)}m_avg"
        wd_col = f"WD_{int(height)}m_avg"
        data[ws_col] = [5.0 + 0.1 * i for i in range(n)]
        data[wd_col] = [225.0] * n
        sensors.append(SensorColumn(
            column_name=ws_col,
            sensor_type="WindSpeed",
            sensor_direction="",
            height=height,
            stat_type="avg",
            unit="m/s",
        ))
        sensors.append(SensorColumn(
            column_name=wd_col,
            sensor_type="WindDirection",
            sensor_direction="",
            height=height,
            stat_type="avg",
            unit="deg",
        ))
    return TimeSeriesData(df=pl.DataFrame(data), sensors=sensors)


def _input(heights: list[float], wind_rose_heights: list[float]) -> SingleMastAnalysisInput:
    return SingleMastAnalysisInput(
        time_series=_paired_time_series(heights),
        parameters=AnalysisParameters(
            air_density=1.225,
            extreme_wind_10min_heights=[],
            extreme_wind_3s_heights=[],
            extreme_wind_gust_factors=[],
            wind_rose_heights=wind_rose_heights,
        ),
        mast_name="M01",
    )


class TestWindRoseSectionHeights:
    def test_from_inputs_filters_frame_to_configured_heights(self) -> None:
        """Atoms must only see the configured subset of computed heights."""
        item = _input([50.0, 100.0, 140.0], wind_rose_heights=[100.0])
        section = WindRoseSection.from_inputs([item])

        atoms = list(section.atoms)
        assert len(atoms) == 4
        for atom in atoms:
            assert sorted(atom.df["height"].unique().to_list()) == [100.0]

    def test_from_inputs_renders_all_configured_heights(self) -> None:
        """Multiple configured heights all reach the atoms."""
        item = _input([50.0, 100.0, 140.0], wind_rose_heights=[50.0, 140.0])
        section = WindRoseSection.from_inputs([item])

        for atom in section.atoms:
            assert sorted(atom.df["height"].unique().to_list()) == [50.0, 140.0]

    def test_from_inputs_raises_on_empty_wind_rose_heights(self) -> None:
        """Empty wind_rose_heights must hard-fail with the field-named message."""
        item = _input([100.0], wind_rose_heights=[])
        with pytest.raises(ValueError, match="wind_rose_heights"):
            WindRoseSection.from_inputs([item])

    def test_from_inputs_error_names_mast_and_recommend(self) -> None:
        """The guard message names the section, mast, and regenerate hint."""
        item = _input([100.0], wind_rose_heights=[])
        with pytest.raises(ValueError, match="M01") as exc_info:
            WindRoseSection.from_inputs([item])
        assert "cleanmast recommend" in str(exc_info.value)

    def test_from_time_series_filters_to_heights(self) -> None:
        """from_time_series applies the same configured-heights filter."""
        ts = _paired_time_series([50.0, 100.0])
        section = WindRoseSection.from_time_series(
            [(ts, "M01", 1.225, [100.0])]
        )
        for atom in section.atoms:
            assert sorted(atom.df["height"].unique().to_list()) == [100.0]

    def test_from_time_series_empty_input_returns_empty_section(self) -> None:
        section = WindRoseSection.from_time_series([])
        assert list(section.atoms) == []
