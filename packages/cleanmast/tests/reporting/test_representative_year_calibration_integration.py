"""Integration test for representative year calibration section — reporting domain.

Ported from tests/assessment/test_representative_year_calibration_integration.py.
Replaces file/report generation with direct Section construction from parameters.
"""

from datetime import datetime
from pathlib import Path

import polars as pl
from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
from cleanmast.subdomains.reporting.model.analysis_input import (
    RepresentativeYearCalibrationPayload,
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.reporting.model.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.section import (
    RepresentativeYearSection,
)
from typst_ir import TypstParagraph, TypstSection, TypstTable

_WS_COL = "WindSpeed_100m_avg [m/s]"


def _create_meso_timeseries() -> TimeSeriesData:
    """Create meso time series spanning multiple years."""
    data_start = datetime(2010, 1, 1)
    data_end = datetime(2020, 6, 30, 23, 0)
    rep_year_start = datetime(2020, 1, 1)
    rep_year_end = datetime(2020, 6, 30, 23, 0)
    climate_ws = 7.0
    rep_year_ws = 7.07

    timestamps = pl.datetime_range(data_start, data_end, "1h", eager=True)
    df = pl.DataFrame({"timestamp": timestamps})
    df = df.with_columns(
        pl.when(
            (pl.col("timestamp") >= rep_year_start)
            & (pl.col("timestamp") <= rep_year_end)
        )
        .then(rep_year_ws)
        .otherwise(climate_ws)
        .alias(_WS_COL)
    )

    sensors = [
        SensorColumn(
            column_name=_WS_COL,
            sensor_type="WindSpeed",
            sensor_direction="",
            height=100.0,
            stat_type="avg",
            unit="m/s",
        )
    ]
    return TimeSeriesData(df=df, sensors=sensors)


class TestRepresentativeYearCalibrationIntegration:
    """Integration test for end-to-end representative year calibration section."""

    def test_section_renders_with_chinese_rep_year_content(self, tmp_path: Path) -> None:
        """Section produces TypstSection containing Chinese rep year headers and summary."""
        meso_data = _create_meso_timeseries()
        payload = RepresentativeYearCalibrationPayload(
            meso_time_series=meso_data,
            meso_name="era5",
            sampling_period="1h",
            rep_year_start=datetime(2020, 1, 1),
            rep_year_end=datetime(2020, 6, 30, 23, 0),
        )
        item = SingleMastAnalysisInput(
            time_series=meso_data,
            parameters=AnalysisParameters(air_density=1.225),
            mast_name="M01",
            representative_year_calibration_payload=payload,
        )
        section = RepresentativeYearSection.from_inputs([item])

        section_node = section.render_ir(tmp_path)

        assert isinstance(section_node, TypstSection)
        assert section_node.heading.text == "代表年订正"

        body_types = {type(item).__name__ for item in section_node.body}
        assert "TypstTable" in body_types
        assert "TypstParagraph" in body_types

        table = next(item for item in section_node.body if isinstance(item, TypstTable))
        assert "测风代表年" in table.headers

        paragraph = next(item for item in section_node.body if isinstance(item, TypstParagraph))
        assert "代表年订正" in paragraph.text
