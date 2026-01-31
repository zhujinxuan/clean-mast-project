"""Tests for top3-constant-shear strategy."""

import math
from pathlib import Path

import numpy as np
import polars as pl
import pytest
import tomli_w
import yaml

from cleanmast.extrapolate.recommend import get_strategy, list_strategies
from cleanmast.extrapolate.recommend.top3_constant_shear import Top3ConstantShearStrategy
from cleanmast.models.reconstruct_meso import (
    MesoSource,
    ReconstructMesoConfiguration,
    ReconstructMesoMast,
    ReconstructMesoModelSpec,
    ReconstructMesoModels,
)
from cleanmast.models.timeseries import TimeRange, TimeSeriesSource


class TestStrategyRegistry:
    """Tests for strategy registration."""

    def test_strategy_registered(self):
        """Test that top3-constant-shear is registered."""
        assert "top3-constant-shear" in list_strategies()

    def test_get_strategy(self):
        """Test getting strategy by name."""
        strategy_class = get_strategy("top3-constant-shear")
        assert strategy_class is Top3ConstantShearStrategy

    def test_unknown_strategy_raises(self):
        """Test that unknown strategy raises ValueError."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            get_strategy("unknown-strategy")


class TestTop3ConstantShearStrategy:
    """Tests for Top3ConstantShearStrategy."""

    @pytest.fixture
    def strategy(self):
        """Create strategy instance."""
        return Top3ConstantShearStrategy()

    @pytest.fixture
    def sample_reconstruct_config(self):
        """Create sample reconstruct-meso configuration."""
        return ReconstructMesoConfiguration(
            masts=[
                ReconstructMesoMast(
                    name="M01",
                    input=TimeSeriesSource(
                        data="./clean/M01.csv",
                        sensors="./clean/M01.sensors.yaml",
                    ),
                    output=TimeSeriesSource(
                        data="./reconstruct-meso/M01.csv",
                        sensors="./reconstruct-meso/M01.sensors.yaml",
                    ),
                    time_range=TimeRange(
                        min="2023-01-01T00:00:00",
                        max="2023-12-31T23:50:00",
                    ),
                    models=ReconstructMesoModels(
                        windspeed=ReconstructMesoModelSpec(
                            method="1-sector",
                            meso_name="era5",
                            model_file="./models/ws_model.json",
                        ),
                        winddirection=ReconstructMesoModelSpec(
                            method="constant-offset",
                            meso_name="era5",
                            model_file="./models/wd_model.json",
                        ),
                    ),
                )
            ],
            mesos=[
                MesoSource(
                    name="era5",
                    input=TimeSeriesSource(
                        data="./meso/era5.csv",
                        sensors="./meso/era5.sensors.yaml",
                    ),
                )
            ],
        )

    @pytest.fixture
    def temp_project(self, tmp_path: Path, sample_reconstruct_config):
        """Create a temporary project with test data."""
        # Create reconstruct-meso output directory
        rm_dir = tmp_path / "reconstruct-meso"
        rm_dir.mkdir()

        # Create sensor metadata with multiple heights
        # IMPORTANT: Include both avg and non-avg sensors to test filtering
        sensors = [
            {
                "columnName": "WS_60m_avg",
                "sensorType": "WindSpeed",
                "sensorDirection": "",
                "height": 60.0,
                "statType": "avg",
                "unit": "m/s",
            },
            {
                "columnName": "WS_80m_avg",
                "sensorType": "WindSpeed",
                "sensorDirection": "",
                "height": 80.0,
                "statType": "avg",
                "unit": "m/s",
            },
            {
                "columnName": "WS_100m_avg",
                "sensorType": "WindSpeed",
                "sensorDirection": "",
                "height": 100.0,
                "statType": "avg",
                "unit": "m/s",
            },
            # Non-avg sensors should be ignored
            {
                "columnName": "WS_100m_max",
                "sensorType": "WindSpeed",
                "sensorDirection": "",
                "height": 100.0,
                "statType": "max",
                "unit": "m/s",
            },
            {
                "columnName": "WS_100m_sd",
                "sensorType": "WindSpeed",
                "sensorDirection": "",
                "height": 100.0,
                "statType": "sd",
                "unit": "m/s",
            },
            # Wind direction sensors
            {
                "columnName": "WD_60m_avg",
                "sensorType": "WindDirection",
                "sensorDirection": "",
                "height": 60.0,
                "statType": "avg",
                "unit": "deg",
            },
            {
                "columnName": "WD_80m_avg",
                "sensorType": "WindDirection",
                "sensorDirection": "",
                "height": 80.0,
                "statType": "avg",
                "unit": "deg",
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

        sensors_file = rm_dir / "M01.sensors.yaml"
        with open(sensors_file, "w") as f:
            yaml.dump({"sensors": sensors}, f)

        # Create wind data with known shear profile
        # Using power law: V = V_ref * (H/H_ref)^alpha
        # True shear = 0.14
        true_shear = 0.14
        ref_speed = 7.0
        ref_height = 60.0

        timestamps = pl.datetime_range(
            start=pl.datetime(2023, 1, 1),
            end=pl.datetime(2023, 1, 1, 2),
            interval="10m",
            eager=True,
        )

        df = pl.DataFrame(
            {
                "timestamp": timestamps,
                "WS_60m_avg": [ref_speed] * len(timestamps),
                "WS_80m_avg": [ref_speed * (80.0 / ref_height) ** true_shear] * len(timestamps),
                "WS_100m_avg": [ref_speed * (100.0 / ref_height) ** true_shear] * len(timestamps),
                "WS_100m_max": [12.0] * len(timestamps),  # Should be ignored
                "WS_100m_sd": [1.5] * len(timestamps),  # Should be ignored
                "WD_60m_avg": [180.0] * len(timestamps),
                "WD_80m_avg": [181.0] * len(timestamps),  # +1 deg over 20m
                "WD_100m_avg": [182.0] * len(timestamps),  # +2 deg over 40m
            }
        )

        data_file = rm_dir / "M01.csv"
        df.write_csv(data_file)

        return tmp_path

    def test_recommend_generates_config(self, strategy, sample_reconstruct_config, temp_project):
        """Test that recommend generates a valid configuration."""
        config = strategy.recommend(
            reconstruct_config=sample_reconstruct_config,
            base_dir=str(temp_project),
            extrapolate_heights=[120.0, 140.0, 160.0],
        )

        assert config.strategy == "top3-constant-shear"
        assert len(config.masts) == 1
        assert config.masts[0].name == "M01"

        # Check per-mast wind speed config
        assert len(config.masts[0].windspeed.heights) == 3
        assert config.masts[0].windspeed.heights[0].height == 120.0
        assert config.masts[0].windspeed.heights[1].height == 140.0
        assert config.masts[0].windspeed.heights[2].height == 160.0

        # Check per-mast wind direction config
        assert len(config.masts[0].winddirection.heights) == 3

    def test_shear_calculated_from_top3_heights(self, strategy, sample_reconstruct_config, temp_project):
        """Test that shear is calculated from top 3 avg sensors only."""
        config = strategy.recommend(
            reconstruct_config=sample_reconstruct_config,
            base_dir=str(temp_project),
            extrapolate_heights=[160.0],
        )

        # Get the reference - should use top height (100m) as reference
        ws_ref = config.masts[0].windspeed.heights[0].references[0]
        assert ws_ref.height == 100.0

        # Shear should be close to 0.14 (our test data)
        assert abs(ws_ref.shear - 0.14) < 0.01

    def test_only_avg_sensors_used(self, strategy, sample_reconstruct_config, temp_project):
        """Test that only avg stat_type sensors are used for shear fitting."""
        # This is validated by the fact that shear ~0.14
        # If max/sd sensors were included, the shear would be different
        config = strategy.recommend(
            reconstruct_config=sample_reconstruct_config,
            base_dir=str(temp_project),
            extrapolate_heights=[160.0],
        )

        ws_ref = config.masts[0].windspeed.heights[0].references[0]
        # True shear is 0.14, if non-avg sensors were used it would be wrong
        assert abs(ws_ref.shear - 0.14) < 0.01

    def test_wind_direction_deg_per_m(self, strategy, sample_reconstruct_config, temp_project):
        """Test that wind direction deg_diff_per_m is calculated correctly."""
        config = strategy.recommend(
            reconstruct_config=sample_reconstruct_config,
            base_dir=str(temp_project),
            extrapolate_heights=[160.0],
        )

        wd_ref = config.masts[0].winddirection.heights[0].references[0]
        # Our test data: 180->182 over 40m = 0.05 deg/m
        assert abs(wd_ref.deg_diff_per_m - 0.05) < 0.01

    def test_output_paths_relative_to_project(self, strategy, sample_reconstruct_config, temp_project):
        """Test that output paths are relative to project directory."""
        config = strategy.recommend(
            reconstruct_config=sample_reconstruct_config,
            base_dir=str(temp_project),
            extrapolate_heights=[160.0],
        )

        assert config.masts[0].output.data == "./extrapolated/M01.csv"
        assert config.masts[0].output.sensors == "./extrapolated/M01.sensors.yaml"

    def test_input_from_reconstruct_meso_output(self, strategy, sample_reconstruct_config, temp_project):
        """Test that input paths come from reconstruct-meso output."""
        config = strategy.recommend(
            reconstruct_config=sample_reconstruct_config,
            base_dir=str(temp_project),
            extrapolate_heights=[160.0],
        )

        # Input should match reconstruct-meso output
        assert config.masts[0].input.data == "./reconstruct-meso/M01.csv"
        assert config.masts[0].input.sensors == "./reconstruct-meso/M01.sensors.yaml"

    def test_skips_existing_heights_per_mast(self, strategy, sample_reconstruct_config, temp_project):
        """Test that existing heights are skipped per-mast during recommend."""
        # Request heights that include existing ones (60, 80, 100) and new ones (120, 160)
        config = strategy.recommend(
            reconstruct_config=sample_reconstruct_config,
            base_dir=str(temp_project),
            extrapolate_heights=[60.0, 80.0, 100.0, 120.0, 160.0],
        )

        # Only non-existing heights should be in config (60, 80, 100 exist in test data)
        ws_target_heights = [h.height for h in config.masts[0].windspeed.heights]
        wd_target_heights = [h.height for h in config.masts[0].winddirection.heights]

        assert ws_target_heights == [120.0, 160.0]
        assert wd_target_heights == [120.0, 160.0]


class TestTop3ConstantShearEdgeCases:
    """Edge case tests for Top3ConstantShearStrategy."""

    @pytest.fixture
    def strategy(self):
        return Top3ConstantShearStrategy()

    def test_fewer_than_3_heights_uses_available(self, strategy, tmp_path):
        """Test that strategy works with fewer than 3 height levels."""
        # Create project with only 2 height levels
        rm_dir = tmp_path / "reconstruct-meso"
        rm_dir.mkdir()

        sensors = [
            {
                "columnName": "WS_80m_avg",
                "sensorType": "WindSpeed",
                "sensorDirection": "",
                "height": 80.0,
                "statType": "avg",
                "unit": "m/s",
            },
            {
                "columnName": "WS_100m_avg",
                "sensorType": "WindSpeed",
                "sensorDirection": "",
                "height": 100.0,
                "statType": "avg",
                "unit": "m/s",
            },
            {
                "columnName": "WD_80m_avg",
                "sensorType": "WindDirection",
                "sensorDirection": "",
                "height": 80.0,
                "statType": "avg",
                "unit": "deg",
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

        # Power law shear = 0.2
        true_shear = 0.2
        timestamps = pl.datetime_range(
            start=pl.datetime(2023, 1, 1),
            end=pl.datetime(2023, 1, 1, 1),
            interval="10m",
            eager=True,
        )

        df = pl.DataFrame(
            {
                "timestamp": timestamps,
                "WS_80m_avg": [8.0] * len(timestamps),
                "WS_100m_avg": [8.0 * (100.0 / 80.0) ** true_shear] * len(timestamps),
                "WD_80m_avg": [180.0] * len(timestamps),
                "WD_100m_avg": [181.0] * len(timestamps),
            }
        )
        df.write_csv(rm_dir / "M01.csv")

        reconstruct_config = ReconstructMesoConfiguration(
            masts=[
                ReconstructMesoMast(
                    name="M01",
                    input=TimeSeriesSource(data="./clean/M01.csv", sensors="./clean/M01.sensors.yaml"),
                    output=TimeSeriesSource(data="./reconstruct-meso/M01.csv", sensors="./reconstruct-meso/M01.sensors.yaml"),
                    time_range=TimeRange(min="2023-01-01T00:00:00", max="2023-12-31T23:50:00"),
                    models=ReconstructMesoModels(
                        windspeed=ReconstructMesoModelSpec(method="1-sector", meso_name="era5", model_file="./m.json"),
                        winddirection=ReconstructMesoModelSpec(method="constant-offset", meso_name="era5", model_file="./m.json"),
                    ),
                )
            ],
            mesos=[MesoSource(name="era5", input=TimeSeriesSource(data="./meso/era5.csv", sensors="./meso/era5.sensors.yaml"))],
        )

        config = strategy.recommend(
            reconstruct_config=reconstruct_config,
            base_dir=str(tmp_path),
            extrapolate_heights=[160.0],
        )

        # Should still work and calculate shear from 2 heights
        assert abs(config.masts[0].windspeed.heights[0].references[0].shear - true_shear) < 0.02

    def test_multiple_masts(self, strategy, tmp_path):
        """Test strategy handles multiple masts."""
        rm_dir = tmp_path / "reconstruct-meso"
        rm_dir.mkdir()

        sensors = [
            {"columnName": "WS_100m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 100.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WS_80m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 80.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WD_100m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 100.0, "statType": "avg", "unit": "deg"},
            {"columnName": "WD_80m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 80.0, "statType": "avg", "unit": "deg"},
        ]

        timestamps = pl.datetime_range(start=pl.datetime(2023, 1, 1), end=pl.datetime(2023, 1, 1, 1), interval="10m", eager=True)
        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_100m_avg": [10.0] * len(timestamps),
            "WS_80m_avg": [9.0] * len(timestamps),
            "WD_100m_avg": [180.0] * len(timestamps),
            "WD_80m_avg": [179.0] * len(timestamps),
        })

        # Create files for both masts
        for mast_name in ["M01", "M02"]:
            with open(rm_dir / f"{mast_name}.sensors.yaml", "w") as f:
                yaml.dump({"sensors": sensors}, f)
            df.write_csv(rm_dir / f"{mast_name}.csv")

        reconstruct_config = ReconstructMesoConfiguration(
            masts=[
                ReconstructMesoMast(
                    name="M01",
                    input=TimeSeriesSource(data="./clean/M01.csv", sensors="./clean/M01.sensors.yaml"),
                    output=TimeSeriesSource(data="./reconstruct-meso/M01.csv", sensors="./reconstruct-meso/M01.sensors.yaml"),
                    time_range=TimeRange(min="2023-01-01T00:00:00", max="2023-12-31T23:50:00"),
                    models=ReconstructMesoModels(
                        windspeed=ReconstructMesoModelSpec(method="1-sector", meso_name="era5", model_file="./m.json"),
                        winddirection=ReconstructMesoModelSpec(method="constant-offset", meso_name="era5", model_file="./m.json"),
                    ),
                ),
                ReconstructMesoMast(
                    name="M02",
                    input=TimeSeriesSource(data="./clean/M02.csv", sensors="./clean/M02.sensors.yaml"),
                    output=TimeSeriesSource(data="./reconstruct-meso/M02.csv", sensors="./reconstruct-meso/M02.sensors.yaml"),
                    time_range=TimeRange(min="2023-01-01T00:00:00", max="2023-12-31T23:50:00"),
                    models=ReconstructMesoModels(
                        windspeed=ReconstructMesoModelSpec(method="1-sector", meso_name="era5", model_file="./m.json"),
                        winddirection=ReconstructMesoModelSpec(method="constant-offset", meso_name="era5", model_file="./m.json"),
                    ),
                ),
            ],
            mesos=[MesoSource(name="era5", input=TimeSeriesSource(data="./meso/era5.csv", sensors="./meso/era5.sensors.yaml"))],
        )

        config = strategy.recommend(
            reconstruct_config=reconstruct_config,
            base_dir=str(tmp_path),
            extrapolate_heights=[160.0],
        )

        assert len(config.masts) == 2
        assert config.masts[0].name == "M01"
        assert config.masts[1].name == "M02"

        # Each mast should have its own windspeed/winddirection config
        assert len(config.masts[0].windspeed.heights) == 1
        assert len(config.masts[1].windspeed.heights) == 1
        assert config.masts[0].windspeed.heights[0].height == 160.0
        assert config.masts[1].windspeed.heights[0].height == 160.0

    def test_wind_direction_across_360_boundary(self, strategy, tmp_path):
        """Test that deg_diff_per_m is calculated correctly when crossing 0/360 boundary."""
        rm_dir = tmp_path / "reconstruct-meso"
        rm_dir.mkdir()

        sensors = [
            {"columnName": "WS_100m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 100.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WS_80m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 80.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WD_60m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 60.0, "statType": "avg", "unit": "deg"},
            {"columnName": "WD_80m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 80.0, "statType": "avg", "unit": "deg"},
            {"columnName": "WD_100m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 100.0, "statType": "avg", "unit": "deg"},
        ]

        with open(rm_dir / "M01.sensors.yaml", "w") as f:
            yaml.dump({"sensors": sensors}, f)

        # Direction crossing 360/0 boundary: 355 -> 358 -> 1
        # This is +3 degrees over 20m twice = 0.15 deg/m
        timestamps = pl.datetime_range(
            start=pl.datetime(2023, 1, 1),
            end=pl.datetime(2023, 1, 1, 1),
            interval="10m",
            eager=True,
        )

        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_100m_avg": [10.0] * len(timestamps),
            "WS_80m_avg": [9.0] * len(timestamps),
            "WD_60m_avg": [355.0] * len(timestamps),
            "WD_80m_avg": [358.0] * len(timestamps),
            "WD_100m_avg": [1.0] * len(timestamps),  # Crossed 360 boundary
        })
        df.write_csv(rm_dir / "M01.csv")

        reconstruct_config = ReconstructMesoConfiguration(
            masts=[
                ReconstructMesoMast(
                    name="M01",
                    input=TimeSeriesSource(data="./clean/M01.csv", sensors="./clean/M01.sensors.yaml"),
                    output=TimeSeriesSource(data="./reconstruct-meso/M01.csv", sensors="./reconstruct-meso/M01.sensors.yaml"),
                    time_range=TimeRange(min="2023-01-01T00:00:00", max="2023-12-31T23:50:00"),
                    models=ReconstructMesoModels(
                        windspeed=ReconstructMesoModelSpec(method="1-sector", meso_name="era5", model_file="./m.json"),
                        winddirection=ReconstructMesoModelSpec(method="constant-offset", meso_name="era5", model_file="./m.json"),
                    ),
                )
            ],
            mesos=[MesoSource(name="era5", input=TimeSeriesSource(data="./meso/era5.csv", sensors="./meso/era5.sensors.yaml"))],
        )

        config = strategy.recommend(
            reconstruct_config=reconstruct_config,
            base_dir=str(tmp_path),
            extrapolate_heights=[160.0],
        )

        # Should correctly calculate ~0.15 deg/m (positive, increasing direction)
        # Not a large negative value from naive 1 - 355 = -354
        wd_ref = config.masts[0].winddirection.heights[0].references[0]
        assert wd_ref.deg_diff_per_m > 0  # Should be positive (direction increasing)
        assert abs(wd_ref.deg_diff_per_m - 0.15) < 0.02  # Should be ~0.15 deg/m

    def test_wind_direction_evenly_distributed(self, strategy, tmp_path):
        """Test deg_diff_per_m with evenly distributed directions (circular mean ~0).

        When directions are evenly distributed (0, 90, 180, 270), the circular mean
        is undefined/0. But per-timestamp differences should still give correct slope.
        """
        rm_dir = tmp_path / "reconstruct-meso"
        rm_dir.mkdir()

        sensors = [
            {"columnName": "WS_100m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 100.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WS_80m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 80.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WD_60m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 60.0, "statType": "avg", "unit": "deg"},
            {"columnName": "WD_80m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 80.0, "statType": "avg", "unit": "deg"},
            {"columnName": "WD_100m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 100.0, "statType": "avg", "unit": "deg"},
        ]

        with open(rm_dir / "M01.sensors.yaml", "w") as f:
            yaml.dump({"sensors": sensors}, f)

        # Evenly distributed directions at 60m: 0, 90, 180, 270 (circular mean = undefined)
        # But each higher level has consistent +2 deg offset per 20m = 0.1 deg/m
        df = pl.DataFrame({
            "timestamp": [
                "2023-01-01T00:00:00",
                "2023-01-01T00:10:00",
                "2023-01-01T00:20:00",
                "2023-01-01T00:30:00",
            ],
            "WS_100m_avg": [10.0, 10.0, 10.0, 10.0],
            "WS_80m_avg": [9.0, 9.0, 9.0, 9.0],
            "WD_60m_avg": [0.0, 90.0, 180.0, 270.0],      # Evenly distributed
            "WD_80m_avg": [2.0, 92.0, 182.0, 272.0],      # +2 deg from 60m
            "WD_100m_avg": [4.0, 94.0, 184.0, 274.0],     # +4 deg from 60m
        })
        df.write_csv(rm_dir / "M01.csv")

        reconstruct_config = ReconstructMesoConfiguration(
            masts=[
                ReconstructMesoMast(
                    name="M01",
                    input=TimeSeriesSource(data="./clean/M01.csv", sensors="./clean/M01.sensors.yaml"),
                    output=TimeSeriesSource(data="./reconstruct-meso/M01.csv", sensors="./reconstruct-meso/M01.sensors.yaml"),
                    time_range=TimeRange(min="2023-01-01T00:00:00", max="2023-12-31T23:50:00"),
                    models=ReconstructMesoModels(
                        windspeed=ReconstructMesoModelSpec(method="1-sector", meso_name="era5", model_file="./m.json"),
                        winddirection=ReconstructMesoModelSpec(method="constant-offset", meso_name="era5", model_file="./m.json"),
                    ),
                )
            ],
            mesos=[MesoSource(name="era5", input=TimeSeriesSource(data="./meso/era5.csv", sensors="./meso/era5.sensors.yaml"))],
        )

        config = strategy.recommend(
            reconstruct_config=reconstruct_config,
            base_dir=str(tmp_path),
            extrapolate_heights=[160.0],
        )

        # Per-timestamp differences:
        # 60m->80m: all +2 deg at Δh=20m
        # 60m->100m: all +4 deg at Δh=40m
        # slope = (20*2*4 + 40*4*4) / (20²*4 + 40²*4) = (160 + 640) / (1600 + 6400) = 800/8000 = 0.1
        wd_ref = config.masts[0].winddirection.heights[0].references[0]
        assert abs(wd_ref.deg_diff_per_m - 0.1) < 0.01

    def test_weighted_references_interpolation(self, strategy, tmp_path):
        """Test that interpolation uses both lower and higher refs with 1/distance weights.

        Existing heights: 60m, 80m, 100m, 140m
        Target: 120m (between 100m and 140m)
        Expected: references to both 100m and 140m with weights based on 1/distance
        - dist to 100m = 20m, dist to 140m = 20m
        - weight_100m = 0.5, weight_140m = 0.5
        """
        rm_dir = tmp_path / "reconstruct-meso"
        rm_dir.mkdir()

        sensors = [
            {"columnName": "WS_60m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 60.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WS_80m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 80.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WS_100m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 100.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WS_140m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 140.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WD_60m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 60.0, "statType": "avg", "unit": "deg"},
            {"columnName": "WD_80m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 80.0, "statType": "avg", "unit": "deg"},
            {"columnName": "WD_100m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 100.0, "statType": "avg", "unit": "deg"},
            {"columnName": "WD_140m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 140.0, "statType": "avg", "unit": "deg"},
        ]

        with open(rm_dir / "M01.sensors.yaml", "w") as f:
            yaml.dump({"sensors": sensors}, f)

        timestamps = pl.datetime_range(
            start=pl.datetime(2023, 1, 1),
            end=pl.datetime(2023, 1, 1, 1),
            interval="10m",
            eager=True,
        )

        # Shear ~0.14
        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_60m_avg": [7.0] * len(timestamps),
            "WS_80m_avg": [7.0 * (80/60)**0.14] * len(timestamps),
            "WS_100m_avg": [7.0 * (100/60)**0.14] * len(timestamps),
            "WS_140m_avg": [7.0 * (140/60)**0.14] * len(timestamps),
            "WD_60m_avg": [180.0] * len(timestamps),
            "WD_80m_avg": [181.0] * len(timestamps),
            "WD_100m_avg": [182.0] * len(timestamps),
            "WD_140m_avg": [184.0] * len(timestamps),
        })
        df.write_csv(rm_dir / "M01.csv")

        reconstruct_config = ReconstructMesoConfiguration(
            masts=[
                ReconstructMesoMast(
                    name="M01",
                    input=TimeSeriesSource(data="./clean/M01.csv", sensors="./clean/M01.sensors.yaml"),
                    output=TimeSeriesSource(data="./reconstruct-meso/M01.csv", sensors="./reconstruct-meso/M01.sensors.yaml"),
                    time_range=TimeRange(min="2023-01-01T00:00:00", max="2023-12-31T23:50:00"),
                    models=ReconstructMesoModels(
                        windspeed=ReconstructMesoModelSpec(method="1-sector", meso_name="era5", model_file="./m.json"),
                        winddirection=ReconstructMesoModelSpec(method="constant-offset", meso_name="era5", model_file="./m.json"),
                    ),
                )
            ],
            mesos=[MesoSource(name="era5", input=TimeSeriesSource(data="./meso/era5.csv", sensors="./meso/era5.sensors.yaml"))],
        )

        # Request 120m which is between 100m and 140m
        config = strategy.recommend(
            reconstruct_config=reconstruct_config,
            base_dir=str(tmp_path),
            extrapolate_heights=[120.0],
        )

        # Should have one height config for 120m
        assert len(config.masts[0].windspeed.heights) == 1
        ws_height_config = config.masts[0].windspeed.heights[0]
        assert ws_height_config.height == 120.0

        # Should have TWO references (100m and 140m)
        assert len(ws_height_config.references) == 2

        # Find lower (100m) and higher (140m) references
        refs_by_height = {r.height: r for r in ws_height_config.references}
        assert 100.0 in refs_by_height
        assert 140.0 in refs_by_height

        # Weights should be 0.5 each (equal distance)
        assert abs(refs_by_height[100.0].weight - 0.5) < 0.01
        assert abs(refs_by_height[140.0].weight - 0.5) < 0.01

        # Weights should sum to 1
        total_weight = sum(r.weight for r in ws_height_config.references)
        assert abs(total_weight - 1.0) < 0.01

    def test_weighted_references_unequal_distance(self, strategy, tmp_path):
        """Test weighted references with unequal distances.

        Existing heights: 60m, 80m, 100m, 160m
        Target: 120m (between 100m and 160m)
        - dist to 100m = 20m, dist to 160m = 40m
        - weight_100m = (1/20) / (1/20 + 1/40) = 0.05 / 0.075 = 2/3
        - weight_160m = (1/40) / (1/20 + 1/40) = 0.025 / 0.075 = 1/3
        """
        rm_dir = tmp_path / "reconstruct-meso"
        rm_dir.mkdir()

        sensors = [
            {"columnName": "WS_60m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 60.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WS_80m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 80.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WS_100m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 100.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WS_160m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 160.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WD_60m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 60.0, "statType": "avg", "unit": "deg"},
            {"columnName": "WD_80m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 80.0, "statType": "avg", "unit": "deg"},
            {"columnName": "WD_100m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 100.0, "statType": "avg", "unit": "deg"},
            {"columnName": "WD_160m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 160.0, "statType": "avg", "unit": "deg"},
        ]

        with open(rm_dir / "M01.sensors.yaml", "w") as f:
            yaml.dump({"sensors": sensors}, f)

        timestamps = pl.datetime_range(
            start=pl.datetime(2023, 1, 1),
            end=pl.datetime(2023, 1, 1, 1),
            interval="10m",
            eager=True,
        )

        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_60m_avg": [7.0] * len(timestamps),
            "WS_80m_avg": [7.5] * len(timestamps),
            "WS_100m_avg": [8.0] * len(timestamps),
            "WS_160m_avg": [9.0] * len(timestamps),
            "WD_60m_avg": [180.0] * len(timestamps),
            "WD_80m_avg": [181.0] * len(timestamps),
            "WD_100m_avg": [182.0] * len(timestamps),
            "WD_160m_avg": [185.0] * len(timestamps),
        })
        df.write_csv(rm_dir / "M01.csv")

        reconstruct_config = ReconstructMesoConfiguration(
            masts=[
                ReconstructMesoMast(
                    name="M01",
                    input=TimeSeriesSource(data="./clean/M01.csv", sensors="./clean/M01.sensors.yaml"),
                    output=TimeSeriesSource(data="./reconstruct-meso/M01.csv", sensors="./reconstruct-meso/M01.sensors.yaml"),
                    time_range=TimeRange(min="2023-01-01T00:00:00", max="2023-12-31T23:50:00"),
                    models=ReconstructMesoModels(
                        windspeed=ReconstructMesoModelSpec(method="1-sector", meso_name="era5", model_file="./m.json"),
                        winddirection=ReconstructMesoModelSpec(method="constant-offset", meso_name="era5", model_file="./m.json"),
                    ),
                )
            ],
            mesos=[MesoSource(name="era5", input=TimeSeriesSource(data="./meso/era5.csv", sensors="./meso/era5.sensors.yaml"))],
        )

        config = strategy.recommend(
            reconstruct_config=reconstruct_config,
            base_dir=str(tmp_path),
            extrapolate_heights=[120.0],
        )

        ws_height_config = config.masts[0].windspeed.heights[0]
        refs_by_height = {r.height: r for r in ws_height_config.references}

        # Weights: 100m gets 2/3, 160m gets 1/3
        assert abs(refs_by_height[100.0].weight - 2/3) < 0.01
        assert abs(refs_by_height[160.0].weight - 1/3) < 0.01

    def test_extrapolation_only_lower_reference(self, strategy, tmp_path):
        """Test that extrapolating above all heights uses only lower reference."""
        rm_dir = tmp_path / "reconstruct-meso"
        rm_dir.mkdir()

        sensors = [
            {"columnName": "WS_60m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 60.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WS_80m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 80.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WS_100m_avg", "sensorType": "WindSpeed", "sensorDirection": "", "height": 100.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "WD_60m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 60.0, "statType": "avg", "unit": "deg"},
            {"columnName": "WD_80m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 80.0, "statType": "avg", "unit": "deg"},
            {"columnName": "WD_100m_avg", "sensorType": "WindDirection", "sensorDirection": "", "height": 100.0, "statType": "avg", "unit": "deg"},
        ]

        with open(rm_dir / "M01.sensors.yaml", "w") as f:
            yaml.dump({"sensors": sensors}, f)

        timestamps = pl.datetime_range(
            start=pl.datetime(2023, 1, 1),
            end=pl.datetime(2023, 1, 1, 1),
            interval="10m",
            eager=True,
        )

        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_60m_avg": [7.0] * len(timestamps),
            "WS_80m_avg": [7.5] * len(timestamps),
            "WS_100m_avg": [8.0] * len(timestamps),
            "WD_60m_avg": [180.0] * len(timestamps),
            "WD_80m_avg": [181.0] * len(timestamps),
            "WD_100m_avg": [182.0] * len(timestamps),
        })
        df.write_csv(rm_dir / "M01.csv")

        reconstruct_config = ReconstructMesoConfiguration(
            masts=[
                ReconstructMesoMast(
                    name="M01",
                    input=TimeSeriesSource(data="./clean/M01.csv", sensors="./clean/M01.sensors.yaml"),
                    output=TimeSeriesSource(data="./reconstruct-meso/M01.csv", sensors="./reconstruct-meso/M01.sensors.yaml"),
                    time_range=TimeRange(min="2023-01-01T00:00:00", max="2023-12-31T23:50:00"),
                    models=ReconstructMesoModels(
                        windspeed=ReconstructMesoModelSpec(method="1-sector", meso_name="era5", model_file="./m.json"),
                        winddirection=ReconstructMesoModelSpec(method="constant-offset", meso_name="era5", model_file="./m.json"),
                    ),
                )
            ],
            mesos=[MesoSource(name="era5", input=TimeSeriesSource(data="./meso/era5.csv", sensors="./meso/era5.sensors.yaml"))],
        )

        # 160m is above all existing heights (max is 100m)
        config = strategy.recommend(
            reconstruct_config=reconstruct_config,
            base_dir=str(tmp_path),
            extrapolate_heights=[160.0],
        )

        ws_height_config = config.masts[0].windspeed.heights[0]

        # Should have only ONE reference (100m, the highest existing)
        assert len(ws_height_config.references) == 1
        assert ws_height_config.references[0].height == 100.0
        assert ws_height_config.references[0].weight == 1.0
