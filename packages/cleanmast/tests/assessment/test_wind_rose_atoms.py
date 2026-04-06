"""Tests for WindRose report atoms."""

from pathlib import Path

import numpy as np
import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_rose import (
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WindRoseSchema,
)


@pytest.fixture
def sample_mast_meta() -> SingleMastMeta:
    return SingleMastMeta(mast_name="M01")


@pytest.fixture
def sample_wind_rose_data() -> pl.DataFrame:
    sector_names = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

    rows = []
    for month in [1, 2, 3]:
        month_name = f"{month}月"
        for height, marker in [(50.0, None), (100.0, None), (120.0, "外推")]:
            base_frequencies = [
                0.03, 0.04, 0.05, 0.06, 0.08, 0.07, 0.06, 0.05,
                0.04, 0.05, 0.06, 0.08, 0.10, 0.12, 0.09, 0.04
            ]

            variation = (height - 100) / 1000
            frequencies = [max(0.01, f + variation * np.random.randn() * 0.01) for f in base_frequencies]

            total = sum(frequencies)
            frequencies = [f / total for f in frequencies]

            base_power = 200 + (height - 50) * 2
            for sector, freq in enumerate(frequencies):
                power = base_power * (1 + 0.3 * np.random.randn()) * (1 + freq * 2)
                rows.append({
                    "month": month,
                    "month_name": month_name,
                    "sector": sector,
                    "sector_name": sector_names[sector],
                    "height": height,
                    "frequency": freq,
                    "wind_power_density": max(50.0, power),
                    "interpolation_marker": marker,
                })

    return pl.DataFrame(rows)


@pytest.fixture
def wind_frequency_rose_atom(
    sample_wind_rose_data: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastMonthlyWindFrequencyRoseAtom:
    return SingleMastMonthlyWindFrequencyRoseAtom.create(
        schema=WindRoseSchema,
        df=sample_wind_rose_data,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_power_rose_atom(
    sample_wind_rose_data: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastWindPowerRoseAtom:
    return SingleMastWindPowerRoseAtom.create(
        schema=WindRoseSchema,
        df=sample_wind_rose_data,
        meta=sample_mast_meta,
    )


class TestSingleMastMonthlyWindFrequencyRoseAtom:
    def test_render_image(self, wind_frequency_rose_atom: SingleMastMonthlyWindFrequencyRoseAtom, tmp_path: Path) -> None:
        image_path = wind_frequency_rose_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, wind_frequency_rose_atom: SingleMastMonthlyWindFrequencyRoseAtom) -> None:
        table = wind_frequency_rose_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
        assert "风向" in table

    def test_render_summary(self, wind_frequency_rose_atom: SingleMastMonthlyWindFrequencyRoseAtom) -> None:
        summary = wind_frequency_rose_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary


class TestSingleMastWindPowerRoseAtom:
    def test_render_image(self, wind_power_rose_atom: SingleMastWindPowerRoseAtom, tmp_path: Path) -> None:
        image_path = wind_power_rose_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, wind_power_rose_atom: SingleMastWindPowerRoseAtom) -> None:
        table = wind_power_rose_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table

    def test_render_summary(self, wind_power_rose_atom: SingleMastWindPowerRoseAtom) -> None:
        summary = wind_power_rose_atom.renderSummary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "测风塔" in summary
