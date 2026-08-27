"""Tests for the cleaning capability sections (Wave 1 placeholders)."""

from datetime import datetime
from pathlib import Path

import polars as pl
from cleanmast.shared.timeseries import SensorColumn, TimeRange, TimeSeriesData
from cleanmast.shared.timeseries.time_series_source import TimeSeriesSource
from cleanmast.subdomains.reporting.model.analysis_input import (
    CleaningAnalysisPayload,
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.reporting.model.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.reporting.subdomains.cleaning import (
    CleaningOverviewSection,
    ImputationCrossMastSection,
    ImputationMesoSection,
    ImputationSameTowerSection,
    TowerShadingSection,
)

SECTIONS = [
    (TowerShadingSection, "塔影效应处理"),
    (ImputationSameTowerSection, "同塔插补"),
    (ImputationCrossMastSection, "异塔插补"),
    (ImputationMesoSection, "中尺度插补"),
]


def _sensor(column: str, height: float, stype: str) -> SensorColumn:
    return SensorColumn(
        column_name=column,
        sensor_type=stype,
        sensor_direction="",
        height=height,
        stat_type="avg",
        unit="m/s" if stype == "WindSpeed" else "deg",
    )


def _input(mast_name: str, with_payload: bool) -> SingleMastAnalysisInput:
    sensors = [_sensor("ws_140", 140.0, "WindSpeed")]
    ts = TimeSeriesData(
        df=pl.DataFrame({
            "timestamp": [datetime(2025, 1, 1)],
            "ws_140": [7.0],
        }),
        sensors=sensors,
    )
    payload = CleaningAnalysisPayload(
        raw_input=TimeSeriesSource(data="./raw/M1.parquet"),
        clean_input=TimeSeriesSource(data="./clean/M1.parquet"),
        tower_shading_input=TimeSeriesSource(data="./tower-shading/M1.parquet"),
        cleaning_heights=[140.0],
        analysis_window=TimeRange(
            min=datetime(2025, 1, 1), max=datetime(2025, 12, 31),
        ),
    ) if with_payload else None
    return SingleMastAnalysisInput(
        time_series=ts,
        parameters=AnalysisParameters(
            air_density=1.225,
            extreme_wind_10min_heights=[],
            extreme_wind_3s_heights=[],
            extreme_wind_gust_factors=[],
        ),
        mast_name=mast_name,
        cleaning_payload=payload,
    )


class TestCleaningPlaceholderSections:
    def test_titles_match_contract(self):
        for section_cls, expected_title in SECTIONS:
            section = section_cls.from_inputs([_input("M1", with_payload=True)])
            assert section.title == expected_title

    def test_renders_heading_and_one_placeholder_line(self, tmp_path):
        for section_cls, _ in SECTIONS:
            if not section_cls._placeholder_text:
                continue  # Wave 2 sections render real content
            section = section_cls.from_inputs([_input("M1", with_payload=True)])
            ir = section.render_ir(Path(tmp_path))
            assert ir.heading.text != ""
            paragraphs = [b for b in ir.body if hasattr(b, "text")]
            assert len(paragraphs) == 1
            assert paragraphs[0].text.endswith("内容待生成。")

    def test_placeholder_carries_mast_names(self):
        section = CleaningOverviewSection.from_inputs(
            [_input("M1", with_payload=False), _input("M2", with_payload=False)]
        )
        atom = section._atoms[0]
        assert atom.meta.mast_names == ["M1", "M2"]

    def test_empty_items_still_render(self, tmp_path):
        section = TowerShadingSection.from_inputs([])
        ir = section.render_ir(Path(tmp_path))
        assert ir.heading.text == "塔影效应处理"
        # No masts: method paragraph + equation still render, no tables.
        assert any(
            "NB/T 31147-2018" in b.text
            for b in ir.body if hasattr(b, "text")
        )
        assert not [b for b in ir.body if hasattr(b, "headers")]
