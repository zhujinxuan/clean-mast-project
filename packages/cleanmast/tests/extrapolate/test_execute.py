"""Tests for extrapolation execution."""

from pathlib import Path

import numpy as np
import polars as pl
import pytest
import tomli_w
import yaml

from cleanmast.extrapolate.config import (
    ExtrapolateConfiguration,
    MastExtrapolateConfig,
    WindDirectionConfig,
    WindDirectionHeightConfig,
    WindDirectionReference,
    WindSpeedConfig,
    WindSpeedHeightConfig,
    WindSpeedReference,
)
from cleanmast.extrapolate.execute import execute_extrapolation, extrapolate_mast
from cleanmast.models.sensor import SensorColumn
from cleanmast.models.timeseries import TimeSeriesData, TimeSeriesSource


class TestExtrapolateMast:
    """Tests for extrapolate_mast function."""

    @pytest.fixture
    def sample_timeseries(self):
        """Create sample time series data."""
        timestamps = pl.datetime_range(
            start=pl.datetime(2023, 1, 1),
            end=pl.datetime(2023, 1, 1, 2),
            interval="10m",
            eager=True,
        )

        df = pl.DataFrame(
            {
                "timestamp": timestamps,
                "WS_100m_avg": [10.0] * len(timestamps),
                "WD_100m_avg": [180.0] * len(timestamps),
            }
        )

        sensors = [
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_100m_avg",
                sensor_type="WindDirection",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

        return TimeSeriesData(df=df, sensors=sensors)

    @pytest.fixture
    def sample_mast_config(self):
        """Create sample per-mast extrapolation configuration."""
        return MastExtrapolateConfig(
            name="M01",
            input=TimeSeriesSource(
                data="./reconstruct-meso/M01.csv",
                sensors="./reconstruct-meso/M01.sensors.yaml",
            ),
            output=TimeSeriesSource(
                data="./extrapolated/M01.csv",
                sensors="./extrapolated/M01.sensors.yaml",
            ),
            windspeed=WindSpeedConfig(
                heights=[
                    WindSpeedHeightConfig(
                        height=160.0,
                        references=[WindSpeedReference(height=100.0, shear=0.14, weight=1.0)],
                    ),
                ]
            ),
            winddirection=WindDirectionConfig(
                heights=[
                    WindDirectionHeightConfig(
                        height=160.0,
                        references=[WindDirectionReference(height=100.0, deg_diff_per_m=0.05, weight=1.0)],
                    ),
                ]
            ),
        )

    def test_extrapolate_adds_new_columns(self, sample_timeseries, sample_mast_config):
        """Test that extrapolation adds new wind speed and direction columns."""
        result = extrapolate_mast(sample_timeseries, sample_mast_config)

        # Original columns should still exist
        assert "WS_100m_avg" in result.df.columns
        assert "WD_100m_avg" in result.df.columns

        # New extrapolated columns should exist
        assert "WS_160m_extrapolated" in result.df.columns
        assert "WD_160m_extrapolated" in result.df.columns

    def test_wind_speed_extrapolation_uses_power_law(self, sample_timeseries, sample_mast_config):
        """Test that wind speed extrapolation uses power law correctly."""
        result = extrapolate_mast(sample_timeseries, sample_mast_config)

        # V2 = V1 * (H2/H1)^shear = 10 * (160/100)^0.14
        expected_speed = 10.0 * (160.0 / 100.0) ** 0.14
        actual_speed = result.df["WS_160m_extrapolated"][0]

        assert abs(actual_speed - expected_speed) < 0.001

    def test_wind_direction_extrapolation_uses_linear_model(self, sample_timeseries, sample_mast_config):
        """Test that wind direction extrapolation uses linear model correctly."""
        result = extrapolate_mast(sample_timeseries, sample_mast_config)

        # WD2 = WD1 + deg_diff_per_m * (H2 - H1) = 180 + 0.05 * 60 = 183
        expected_dir = 180.0 + 0.05 * (160.0 - 100.0)
        actual_dir = result.df["WD_160m_extrapolated"][0]

        assert abs(actual_dir - expected_dir) < 0.001

    def test_extrapolated_sensors_added_to_metadata(self, sample_timeseries, sample_mast_config):
        """Test that extrapolated sensor metadata is added."""
        result = extrapolate_mast(sample_timeseries, sample_mast_config)

        # Should have original sensors plus 2 new ones
        assert len(result.sensors) == 4

        # Find the new wind speed sensor
        ws_sensor = next(
            (s for s in result.sensors if s.column_name == "WS_160m_extrapolated"),
            None,
        )
        assert ws_sensor is not None
        assert ws_sensor.sensor_type == "WindSpeed"
        assert ws_sensor.height == 160.0
        assert ws_sensor.stat_type == "avg"
        assert ws_sensor.unit == "m/s"

    def test_multiple_target_heights(self, sample_timeseries):
        """Test extrapolation to multiple target heights."""
        mast_config = MastExtrapolateConfig(
            name="M01",
            input=TimeSeriesSource(data="./in.csv", sensors="./in.yaml"),
            output=TimeSeriesSource(data="./out.csv", sensors="./out.yaml"),
            windspeed=WindSpeedConfig(
                heights=[
                    WindSpeedHeightConfig(
                        height=120.0,
                        references=[WindSpeedReference(height=100.0, shear=0.14)],
                    ),
                    WindSpeedHeightConfig(
                        height=140.0,
                        references=[WindSpeedReference(height=100.0, shear=0.14)],
                    ),
                    WindSpeedHeightConfig(
                        height=160.0,
                        references=[WindSpeedReference(height=100.0, shear=0.14)],
                    ),
                ]
            ),
            winddirection=WindDirectionConfig(
                heights=[
                    WindDirectionHeightConfig(
                        height=120.0,
                        references=[WindDirectionReference(height=100.0, deg_diff_per_m=0.05)],
                    ),
                    WindDirectionHeightConfig(
                        height=140.0,
                        references=[WindDirectionReference(height=100.0, deg_diff_per_m=0.05)],
                    ),
                    WindDirectionHeightConfig(
                        height=160.0,
                        references=[WindDirectionReference(height=100.0, deg_diff_per_m=0.05)],
                    ),
                ]
            ),
        )

        result = extrapolate_mast(sample_timeseries, mast_config)

        # Should have 3 new wind speed and 3 new wind direction columns
        assert "WS_120m_extrapolated" in result.df.columns
        assert "WS_140m_extrapolated" in result.df.columns
        assert "WS_160m_extrapolated" in result.df.columns
        assert "WD_120m_extrapolated" in result.df.columns
        assert "WD_140m_extrapolated" in result.df.columns
        assert "WD_160m_extrapolated" in result.df.columns


class TestExecuteExtrapolation:
    """Tests for execute_extrapolation function."""

    @pytest.fixture
    def temp_project(self, tmp_path: Path):
        """Create a temporary project with test data."""
        # Create reconstruct-meso output directory
        rm_dir = tmp_path / "reconstruct-meso"
        rm_dir.mkdir()

        # Create sensor metadata
        sensors = [
            {
                "columnName": "WS_100m_avg",
                "sensorType": "WindSpeed",
                "sensorDirection": "",
                "height": 100.0,
                "statType": "avg",
                "unit": "m/s",
            },
            {
                "columnName": "WD_100m_avg",
                "sensorType": "WindDirection",
                "sensorDirection": "",
                "height": 100.0,
                "statType": "avg",
                "unit": "deg",
            },
        ]

        with open(rm_dir / "M01.sensors.yaml", "w") as f:
            yaml.dump({"sensors": sensors}, f)

        # Create wind data
        timestamps = pl.datetime_range(
            start=pl.datetime(2023, 1, 1),
            end=pl.datetime(2023, 1, 1, 2),
            interval="10m",
            eager=True,
        )

        df = pl.DataFrame(
            {
                "timestamp": timestamps,
                "WS_100m_avg": [10.0] * len(timestamps),
                "WD_100m_avg": [180.0] * len(timestamps),
            }
        )
        df.write_csv(rm_dir / "M01.csv")

        # Create config with per-mast structure
        config_data = {
            "strategy": "top3-constant-shear",
            "masts": [
                {
                    "name": "M01",
                    "input": {
                        "data": "./reconstruct-meso/M01.csv",
                        "sensors": "./reconstruct-meso/M01.sensors.yaml",
                    },
                    "output": {
                        "data": "./extrapolated/M01.csv",
                        "sensors": "./extrapolated/M01.sensors.yaml",
                    },
                    "windspeed": {
                        "heights": [
                            {
                                "height": 160.0,
                                "references": [{"height": 100.0, "shear": 0.14, "weight": 1.0}],
                            }
                        ]
                    },
                    "winddirection": {
                        "heights": [
                            {
                                "height": 160.0,
                                "references": [{"height": 100.0, "deg_diff_per_m": 0.05, "weight": 1.0}],
                            }
                        ]
                    },
                }
            ],
        }

        with open(tmp_path / "vertical-extrapolate.toml", "wb") as f:
            tomli_w.dump(config_data, f)

        return tmp_path

    def test_execute_creates_output_files(self, temp_project):
        """Test that execute creates output CSV and sensors files."""
        config_path = temp_project / "vertical-extrapolate.toml"

        execute_extrapolation(str(config_path))

        # Check output files exist
        output_csv = temp_project / "extrapolated" / "M01.csv"
        output_sensors = temp_project / "extrapolated" / "M01.sensors.yaml"

        assert output_csv.exists()
        assert output_sensors.exists()

    def test_execute_output_contains_extrapolated_data(self, temp_project):
        """Test that output contains extrapolated columns."""
        config_path = temp_project / "vertical-extrapolate.toml"

        execute_extrapolation(str(config_path))

        # Read output
        output_csv = temp_project / "extrapolated" / "M01.csv"
        df = pl.read_csv(output_csv)

        # Should have extrapolated columns
        assert "WS_160m_extrapolated" in df.columns
        assert "WD_160m_extrapolated" in df.columns

        # Check values
        expected_speed = 10.0 * (160.0 / 100.0) ** 0.14
        assert abs(df["WS_160m_extrapolated"][0] - expected_speed) < 0.001

    def test_execute_output_sensors_has_extrapolated_metadata(self, temp_project):
        """Test that output sensors file has extrapolated sensor metadata."""
        config_path = temp_project / "vertical-extrapolate.toml"

        execute_extrapolation(str(config_path))

        # Read output sensors
        output_sensors = temp_project / "extrapolated" / "M01.sensors.yaml"
        with open(output_sensors) as f:
            sensors_data = yaml.safe_load(f)

        # Should have 4 sensors (2 original + 2 extrapolated)
        assert len(sensors_data["sensors"]) == 4

        # Find extrapolated wind speed sensor
        ws_sensor = next(
            (s for s in sensors_data["sensors"] if s["columnName"] == "WS_160m_extrapolated"),
            None,
        )
        assert ws_sensor is not None
        assert ws_sensor["sensorType"] == "WindSpeed"
        assert ws_sensor["height"] == 160.0
