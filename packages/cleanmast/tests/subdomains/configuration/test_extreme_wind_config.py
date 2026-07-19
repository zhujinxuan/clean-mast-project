"""Tests for extreme-wind configuration discovery and MastRef fields."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import tomli
import tomli_w
from cleanmast.subdomains.configuration import (
    ExtremeWindGustFactor,
    MastRef,
)
from cleanmast.subdomains.configuration.services.recommend_report import (
    _discover_extreme_wind_heights,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import (
    SensorColumn,
)
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sensor(
    sensor_type: str = "WindSpeed",
    stat_type: str = "avg",
    height: float = 100.0,
    column_name: str = "",
    sensor_direction: str = "",
    unit: str = "m/s",
) -> SensorColumn:
    if not column_name:
        column_name = f"{sensor_type}_{height}m_{stat_type} [{unit}]"
    return SensorColumn(
        column_name=column_name,
        sensor_type=sensor_type,
        sensor_direction=sensor_direction,
        height=height,
        stat_type=stat_type,
        unit=unit,
    )


# ---------------------------------------------------------------------------
# ExtremeWindGustFactor model
# ---------------------------------------------------------------------------

class TestExtremeWindGustFactor:
    """Tests for the ExtremeWindGustFactor frozen model."""

    def test_default_gust_factor(self):
        gf = ExtremeWindGustFactor(height=100.0)
        assert gf.height == 100.0
        assert gf.gust_factor == 1.4

    def test_custom_gust_factor(self):
        gf = ExtremeWindGustFactor(height=120.0, gust_factor=1.35)
        assert gf.gust_factor == 1.35

    def test_is_frozen(self):
        gf = ExtremeWindGustFactor(height=100.0)
        with pytest.raises(ValidationError):
            gf.gust_factor = 1.5

    def test_serialize_json_mode(self):
        gf = ExtremeWindGustFactor(height=100.0)
        data = gf.model_dump(mode="json")
        assert data == {"height": 100.0, "gust_factor": 1.4}

    def test_exclude_none_roundtrip(self):
        """TOML save/load: model_dump(exclude_none=True) round-trips."""
        gf = ExtremeWindGustFactor(height=100.0)
        dumped = gf.model_dump(mode="json", exclude_none=True)
        rehydrated = ExtremeWindGustFactor(**dumped)
        assert rehydrated.height == 100.0
        assert rehydrated.gust_factor == 1.4


# ---------------------------------------------------------------------------
# _discover_extreme_wind_heights
# ---------------------------------------------------------------------------

class TestDiscoverExtremeWindHeights:
    """Tests for the _discover_extreme_wind_heights sensor-to-config logic."""

    def test_avg_only_for_10min(self):
        """10min list = WindSpeed/avg only, sorted, within 120–160."""
        sensors = [
            _sensor("WindSpeed", "avg", 150.0),
            _sensor("WindSpeed", "max", 150.0),  # max → not in 10min
            _sensor("WindSpeed", "sd", 150.0),    # sd → not in 10min
            _sensor("WindDirection", "avg", 150.0),  # wrong sensor
        ]
        ten_min, three_sec, gust_factors = _discover_extreme_wind_heights(sensors)
        assert ten_min == [150.0]
        assert three_sec == [150.0]  # max sensor at 150
        assert len(gust_factors) == 1

    def test_max_only_for_3s(self):
        """3s list = WindSpeed/max only, sorted, within 120–160."""
        sensors = [
            _sensor("WindSpeed", "max", 120.0),
            _sensor("WindSpeed", "avg", 130.0),
            _sensor("WindSpeed", "max", 160.0),
            _sensor("WindSpeed", "avg", 160.0),
        ]
        ten_min, three_sec, gust_factors = _discover_extreme_wind_heights(sensors)
        assert ten_min == [130.0, 160.0]
        assert three_sec == [120.0, 160.0]
        assert len(gust_factors) == 2

    def test_edge_heights_boundary(self):
        """Heights exactly at 120.0 and 160.0 are included; 119.9/160.1 excluded."""
        sensors = [
            _sensor("WindSpeed", "avg", 119.9),
            _sensor("WindSpeed", "avg", 120.0),
            _sensor("WindSpeed", "avg", 160.0),
            _sensor("WindSpeed", "avg", 160.1),
        ]
        ten_min, three_sec, _ = _discover_extreme_wind_heights(sensors)
        assert ten_min == [120.0, 160.0]

    def test_edge_heights_3s_boundary(self):
        """3s edges: 119.9 excluded, 120.0 included, 160.0 included, 160.1 excluded."""
        sensors = [
            _sensor("WindSpeed", "max", 119.9),
            _sensor("WindSpeed", "max", 120.0),
            _sensor("WindSpeed", "max", 160.0),
            _sensor("WindSpeed", "max", 160.1),
        ]
        _, three_sec, _ = _discover_extreme_wind_heights(sensors)
        assert three_sec == [120.0, 160.0]

    def test_gust_factor_covers_every_10min_height(self):
        """Every 10min height gets a gust factor entry with default 1.4."""
        sensors = [
            _sensor("WindSpeed", "avg", 120.0),
            _sensor("WindSpeed", "avg", 140.0),
            _sensor("WindSpeed", "avg", 160.0),
        ]
        ten_min, _, gust_factors = _discover_extreme_wind_heights(sensors)
        assert ten_min == [120.0, 140.0, 160.0]
        assert [gf.height for gf in gust_factors] == [120.0, 140.0, 160.0]
        for gf in gust_factors:
            assert gf.gust_factor == 1.4

    def test_no_qualifying_sensors(self):
        """Mast with no WindSpeed sensors in 120–160 returns empty lists."""
        sensors = [
            _sensor("WindSpeed", "avg", 60.0),
            _sensor("WindSpeed", "max", 80.0),
            _sensor("WindDirection", "avg", 140.0),
        ]
        ten_min, three_sec, gust_factors = _discover_extreme_wind_heights(sensors)
        assert ten_min == []
        assert three_sec == []
        assert gust_factors == []

    def test_sorted_output(self):
        """Results are sorted ascending by height."""
        sensors = [
            _sensor("WindSpeed", "avg", 160.0),
            _sensor("WindSpeed", "avg", 120.0),
            _sensor("WindSpeed", "avg", 140.0),
            _sensor("WindSpeed", "max", 150.0),
            _sensor("WindSpeed", "max", 125.0),
        ]
        ten_min, three_sec, gust_factors = _discover_extreme_wind_heights(sensors)
        assert ten_min == [120.0, 140.0, 160.0]
        assert three_sec == [125.0, 150.0]
        assert [gf.height for gf in gust_factors] == ten_min

    def test_fill_height_without_nearby_both_sensor_stays(self):
        """Fill height with no real both-sensor height within 10m stays in 10min list."""
        # Real 150m has avg but no max → not a both-sensor height
        sensors = [
            _sensor("WindSpeed", "avg", 130.0, column_name="WindSpeed_130m_avg_fill:interpolated"),
            _sensor("WindSpeed", "avg", 150.0, column_name="WindSpeed_150m_avg [m/s]"),
        ]
        ten_min, _, _ = _discover_extreme_wind_heights(sensors)
        assert ten_min == [130.0, 150.0]

    # --- Spec exclusion rule tests ---

    def test_fill_excluded_when_bracketed_by_both_sensor(self):
        """Fill 125m excluded: real 120m & 130m (both avg+max) within ≤10m."""
        sensors = [
            _sensor("WindSpeed", "avg", 120.0, column_name="WindSpeed_120m_avg [m/s]"),
            _sensor("WindSpeed", "max", 120.0, column_name="WindSpeed_120m_max [m/s]"),
            _sensor("WindSpeed", "avg", 125.0, column_name="WindSpeed_125m_avg_fill:interpolated"),
            _sensor("WindSpeed", "avg", 130.0, column_name="WindSpeed_130m_avg [m/s]"),
            _sensor("WindSpeed", "max", 130.0, column_name="WindSpeed_130m_max [m/s]"),
        ]
        ten_min, three_sec, gust_factors = _discover_extreme_wind_heights(sensors)
        assert ten_min == [120.0, 130.0]
        assert three_sec == [120.0, 130.0]
        assert [gf.height for gf in gust_factors] == [120.0, 130.0]

    def test_fill_excluded_at_exactly_10m_distance(self):
        """Fill 130m excluded: real 120m & 140m (both avg+max), 130-120=10 ≤ 10."""
        sensors = [
            _sensor("WindSpeed", "avg", 120.0, column_name="WindSpeed_120m_avg [m/s]"),
            _sensor("WindSpeed", "max", 120.0, column_name="WindSpeed_120m_max [m/s]"),
            _sensor("WindSpeed", "avg", 130.0, column_name="WindSpeed_130m_avg_fill:interpolated"),
            _sensor("WindSpeed", "avg", 140.0, column_name="WindSpeed_140m_avg [m/s]"),
            _sensor("WindSpeed", "max", 140.0, column_name="WindSpeed_140m_max [m/s]"),
        ]
        ten_min, _, _ = _discover_extreme_wind_heights(sensors)
        assert ten_min == [120.0, 140.0]

    def test_remote_fill_height_stays(self):
        """Fill 150m stays: nearest real both-sensor at 130m, 150-130=20 > 10."""
        sensors = [
            _sensor("WindSpeed", "avg", 120.0, column_name="WindSpeed_120m_avg [m/s]"),
            _sensor("WindSpeed", "max", 120.0, column_name="WindSpeed_120m_max [m/s]"),
            _sensor("WindSpeed", "avg", 130.0, column_name="WindSpeed_130m_avg [m/s]"),
            _sensor("WindSpeed", "max", 130.0, column_name="WindSpeed_130m_max [m/s]"),
            _sensor("WindSpeed", "avg", 150.0, column_name="WindSpeed_150m_avg_fill:interpolated"),
        ]
        ten_min, _, gust_factors = _discover_extreme_wind_heights(sensors)
        assert ten_min == [120.0, 130.0, 150.0]
        assert [gf.height for gf in gust_factors] == [120.0, 130.0, 150.0]

    def test_real_avg_only_does_not_trigger_exclusion(self):
        """Real heights with avg but no max do NOT trigger fill exclusion."""
        # 120m real: avg only; 130m real: avg only; no both-sensor heights exist
        sensors = [
            _sensor("WindSpeed", "avg", 120.0, column_name="WindSpeed_120m_avg [m/s]"),
            _sensor("WindSpeed", "avg", 125.0, column_name="WindSpeed_125m_avg_fill:interpolated"),
            _sensor("WindSpeed", "avg", 130.0, column_name="WindSpeed_130m_avg [m/s]"),
        ]
        ten_min, _, _ = _discover_extreme_wind_heights(sensors)
        # No real both-sensor heights → fill 125m stays
        assert ten_min == [120.0, 125.0, 130.0]

    def test_empty_sensors_list(self):
        """Empty sensor list → empty results."""
        ten_min, three_sec, gust_factors = _discover_extreme_wind_heights([])
        assert ten_min == []
        assert three_sec == []
        assert gust_factors == []


# ---------------------------------------------------------------------------
# MastRef extreme-wind fields
# ---------------------------------------------------------------------------

class TestMastRefExtremeWind:
    """Tests for MastRef extreme-wind optional fields and TOML round-trips."""

    # Shared extreme-wind fixtures
    _EW_10MIN: list[float] = [120.0, 140.0, 160.0]
    _EW_3S: list[float] = [140.0, 160.0]
    _EW_GUST: list[ExtremeWindGustFactor] = [
        ExtremeWindGustFactor(height=120.0),
        ExtremeWindGustFactor(height=140.0, gust_factor=1.35),
        ExtremeWindGustFactor(height=160.0),
    ]

    def test_new_fields_default_to_none(self):
        """MastRef without extreme-wind args has None for all three fields."""
        mr = MastRef(
            name="M1",
            air_density=1.225,
            input=TimeSeriesSource(data="./data/M1.parquet"),
        )
        assert mr.extreme_wind_10min_heights is None
        assert mr.extreme_wind_3s_heights is None
        assert mr.extreme_wind_gust_factors is None

    def test_fields_set_explicitly(self):
        """Fields can be set to explicit values."""
        mr = MastRef(
            name="M1",
            air_density=1.225,
            input=TimeSeriesSource(data="./data/M1.parquet"),
            extreme_wind_10min_heights=self._EW_10MIN,
            extreme_wind_3s_heights=self._EW_3S,
            extreme_wind_gust_factors=self._EW_GUST,
        )
        assert mr.extreme_wind_10min_heights == [120.0, 140.0, 160.0]
        assert mr.extreme_wind_3s_heights == [140.0, 160.0]
        assert mr.extreme_wind_gust_factors is not None
        assert len(mr.extreme_wind_gust_factors) == 3

    def test_mastref_is_frozen(self):
        """MastRef with new fields is still frozen."""
        mr = MastRef(
            name="M1",
            air_density=1.225,
            input=TimeSeriesSource(data="./data/M1.parquet"),
            extreme_wind_10min_heights=self._EW_10MIN,
        )
        with pytest.raises(ValidationError):
            mr.extreme_wind_10min_heights = [100.0]

    def test_serialize_excludes_none(self):
        """model_dump(exclude_none=True) omits None fields."""
        mr = MastRef(
            name="M1",
            air_density=1.225,
            input=TimeSeriesSource(data="./data/M1.parquet"),
        )
        data = mr.model_dump(mode="json", exclude_none=True)
        assert "extreme_wind_10min_heights" not in data
        assert "extreme_wind_3s_heights" not in data
        assert "extreme_wind_gust_factors" not in data

    def test_serialize_includes_set_fields(self):
        """model_dump(exclude_none=True) includes non-None extreme-wind fields."""
        mr = MastRef(
            name="M1",
            air_density=1.225,
            input=TimeSeriesSource(data="./data/M1.parquet"),
            extreme_wind_10min_heights=self._EW_10MIN,
            extreme_wind_3s_heights=self._EW_3S,
            extreme_wind_gust_factors=self._EW_GUST,
        )
        data = mr.model_dump(mode="json", exclude_none=True)
        assert data["extreme_wind_10min_heights"] == [120.0, 140.0, 160.0]
        assert data["extreme_wind_3s_heights"] == [140.0, 160.0]
        assert len(data["extreme_wind_gust_factors"]) == 3

    def test_toml_roundtrip_with_fields(self):
        """TOML save + load preserves extreme-wind fields exactly."""
        mr = MastRef(
            name="M1",
            air_density=1.225,
            input=TimeSeriesSource(data="./data/M1.parquet"),
            extreme_wind_10min_heights=self._EW_10MIN,
            extreme_wind_3s_heights=self._EW_3S,
            extreme_wind_gust_factors=self._EW_GUST,
        )
        data = mr.model_dump(mode="json", exclude_none=True)
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False, mode="wb") as f:
            tmp_path = Path(f.name)
            tomli_w.dump(data, f)

        with open(tmp_path, "rb") as f:
            loaded_data = tomli.load(f)
        rehydrated = MastRef(**loaded_data)
        assert rehydrated.extreme_wind_10min_heights == [120.0, 140.0, 160.0]
        assert rehydrated.extreme_wind_3s_heights == [140.0, 160.0]
        assert rehydrated.extreme_wind_gust_factors is not None
        assert len(rehydrated.extreme_wind_gust_factors) == 3
        assert rehydrated.extreme_wind_gust_factors[0].height == 120.0
        assert rehydrated.extreme_wind_gust_factors[0].gust_factor == 1.4
        tmp_path.unlink()

    def test_old_toml_without_fields_loads(self):
        """A TOML without extreme-wind fields loads with None defaults."""
        old_data = {
            "name": "MOld",
            "air_density": 1.20,
            "input": {"data": "./data/MOld.parquet"},
            "turbulence_heights": [100.0, 120.0],
        }
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False, mode="wb") as f:
            tmp_path = Path(f.name)
            tomli_w.dump(old_data, f)

        with open(tmp_path, "rb") as f:
            loaded_data = tomli.load(f)
        mr = MastRef(**loaded_data)
        assert mr.name == "MOld"
        assert mr.turbulence_heights == [100.0, 120.0]
        assert mr.extreme_wind_10min_heights is None
        assert mr.extreme_wind_3s_heights is None
        assert mr.extreme_wind_gust_factors is None
        tmp_path.unlink()

    def test_empty_lists_in_fields(self):
        """Fields accept empty lists explicitly."""
        mr = MastRef(
            name="M1",
            air_density=1.225,
            input=TimeSeriesSource(data="./data/M1.parquet"),
            extreme_wind_10min_heights=[],
            extreme_wind_3s_heights=[],
            extreme_wind_gust_factors=[],
        )
        assert mr.extreme_wind_10min_heights == []
        assert mr.extreme_wind_3s_heights == []
        assert mr.extreme_wind_gust_factors == []
