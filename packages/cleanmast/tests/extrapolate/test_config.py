"""Tests for extrapolation configuration models."""

import tempfile
from pathlib import Path

import pytest
import tomli
import tomli_w

from cleanmast.extrapolate.config import (
    ExtrapolateConfiguration,
    MastExtrapolateConfig,
    WindDirectionConfig,
    WindDirectionHeightConfig,
    WindDirectionReference,
    WindSpeedConfig,
    WindSpeedHeightConfig,
    WindSpeedReference,
    load_extrapolate_config,
)
from cleanmast.models.timeseries import TimeSeriesSource


class TestWindSpeedReference:
    """Tests for WindSpeedReference model."""

    def test_create_reference(self):
        """Test creating a wind speed reference."""
        ref = WindSpeedReference(
            height=100.0,
            shear=0.15,
            weight=1.0,
        )

        assert ref.height == 100.0
        assert ref.shear == 0.15
        assert ref.weight == 1.0

    def test_default_weight(self):
        """Test default weight is 1.0."""
        ref = WindSpeedReference(height=100.0, shear=0.15)
        assert ref.weight == 1.0


class TestWindSpeedHeightConfig:
    """Tests for WindSpeedHeightConfig model."""

    def test_create_height_config(self):
        """Test creating a height configuration."""
        config = WindSpeedHeightConfig(
            height=160.0,
            references=[
                WindSpeedReference(height=100.0, shear=0.15, weight=1.0),
            ],
        )

        assert config.height == 160.0
        assert len(config.references) == 1
        assert config.references[0].shear == 0.15

    def test_multiple_references(self):
        """Test height config with multiple references."""
        config = WindSpeedHeightConfig(
            height=160.0,
            references=[
                WindSpeedReference(height=100.0, shear=0.14, weight=0.6),
                WindSpeedReference(height=80.0, shear=0.16, weight=0.4),
            ],
        )

        assert len(config.references) == 2
        total_weight = sum(r.weight for r in config.references)
        assert total_weight == 1.0


class TestWindDirectionReference:
    """Tests for WindDirectionReference model."""

    def test_create_reference(self):
        """Test creating a wind direction reference."""
        ref = WindDirectionReference(
            height=100.0,
            deg_diff_per_m=0.05,
            weight=1.0,
        )

        assert ref.height == 100.0
        assert ref.deg_diff_per_m == 0.05
        assert ref.weight == 1.0


class TestWindDirectionHeightConfig:
    """Tests for WindDirectionHeightConfig model."""

    def test_create_height_config(self):
        """Test creating a height configuration."""
        config = WindDirectionHeightConfig(
            height=160.0,
            references=[
                WindDirectionReference(height=100.0, deg_diff_per_m=0.05, weight=1.0),
            ],
        )

        assert config.height == 160.0
        assert len(config.references) == 1


class TestMastExtrapolateConfig:
    """Tests for MastExtrapolateConfig model."""

    def test_create_mast_config(self):
        """Test creating a mast extrapolation config with per-mast windspeed/winddirection."""
        config = MastExtrapolateConfig(
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
                        references=[WindSpeedReference(height=100.0, shear=0.15)],
                    )
                ]
            ),
            winddirection=WindDirectionConfig(
                heights=[
                    WindDirectionHeightConfig(
                        height=160.0,
                        references=[WindDirectionReference(height=100.0, deg_diff_per_m=0.05)],
                    )
                ]
            ),
        )

        assert config.name == "M01"
        assert "reconstruct-meso" in config.input.data
        assert "extrapolated" in config.output.data
        assert len(config.windspeed.heights) == 1
        assert config.windspeed.heights[0].height == 160.0


class TestExtrapolateConfiguration:
    """Tests for ExtrapolateConfiguration model."""

    def test_create_full_configuration(self):
        """Test creating a full extrapolation configuration with per-mast config."""
        config = ExtrapolateConfiguration(
            strategy="top3-constant-shear",
            masts=[
                MastExtrapolateConfig(
                    name="M01",
                    input=TimeSeriesSource(data="./in/M01.csv", sensors="./in/M01.sensors.yaml"),
                    output=TimeSeriesSource(data="./out/M01.csv", sensors="./out/M01.sensors.yaml"),
                    windspeed=WindSpeedConfig(
                        heights=[
                            WindSpeedHeightConfig(
                                height=160.0,
                                references=[WindSpeedReference(height=100.0, shear=0.15)],
                            )
                        ]
                    ),
                    winddirection=WindDirectionConfig(
                        heights=[
                            WindDirectionHeightConfig(
                                height=160.0,
                                references=[WindDirectionReference(height=100.0, deg_diff_per_m=0.05)],
                            )
                        ]
                    ),
                )
            ],
        )

        assert config.strategy == "top3-constant-shear"
        assert len(config.masts) == 1
        assert len(config.masts[0].windspeed.heights) == 1
        assert config.masts[0].windspeed.heights[0].height == 160.0

    def test_create_from_nested_dict(self):
        """Test creating configuration from nested dict (like TOML)."""
        data = {
            "strategy": "top3-constant-shear",
            "masts": [
                {
                    "name": "M01",
                    "input": {"data": "./in/data.csv", "sensors": "./in/sensors.yaml"},
                    "output": {"data": "./out/data.csv", "sensors": "./out/sensors.yaml"},
                    "windspeed": {
                        "heights": [
                            {
                                "height": 160.0,
                                "references": [{"height": 100.0, "shear": 0.15, "weight": 1.0}],
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

        config = ExtrapolateConfiguration(**data)

        assert config.strategy == "top3-constant-shear"
        assert config.masts[0].name == "M01"
        assert config.masts[0].windspeed.heights[0].references[0].shear == 0.15

    def test_multiple_extrapolation_heights(self):
        """Test configuration with multiple target heights per mast."""
        config = ExtrapolateConfiguration(
            strategy="top3-constant-shear",
            masts=[
                MastExtrapolateConfig(
                    name="M01",
                    input=TimeSeriesSource(data="./in.csv", sensors="./in.yaml"),
                    output=TimeSeriesSource(data="./out.csv", sensors="./out.yaml"),
                    windspeed=WindSpeedConfig(
                        heights=[
                            WindSpeedHeightConfig(
                                height=120.0,
                                references=[WindSpeedReference(height=100.0, shear=0.15)],
                            ),
                            WindSpeedHeightConfig(
                                height=140.0,
                                references=[WindSpeedReference(height=100.0, shear=0.15)],
                            ),
                            WindSpeedHeightConfig(
                                height=160.0,
                                references=[WindSpeedReference(height=100.0, shear=0.15)],
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
            ],
        )

        assert len(config.masts[0].windspeed.heights) == 3
        assert config.masts[0].windspeed.heights[0].height == 120.0
        assert config.masts[0].windspeed.heights[2].height == 160.0

    def test_different_heights_per_mast(self):
        """Test configuration where different masts have different extrapolation heights."""
        config = ExtrapolateConfiguration(
            strategy="top3-constant-shear",
            masts=[
                MastExtrapolateConfig(
                    name="M01",
                    input=TimeSeriesSource(data="./in/M01.csv", sensors="./in/M01.yaml"),
                    output=TimeSeriesSource(data="./out/M01.csv", sensors="./out/M01.yaml"),
                    windspeed=WindSpeedConfig(
                        heights=[
                            WindSpeedHeightConfig(
                                height=160.0,
                                references=[WindSpeedReference(height=100.0, shear=0.15)],
                            ),
                        ]
                    ),
                    winddirection=WindDirectionConfig(heights=[]),
                ),
                MastExtrapolateConfig(
                    name="M02",
                    input=TimeSeriesSource(data="./in/M02.csv", sensors="./in/M02.yaml"),
                    output=TimeSeriesSource(data="./out/M02.csv", sensors="./out/M02.yaml"),
                    windspeed=WindSpeedConfig(
                        heights=[
                            WindSpeedHeightConfig(
                                height=120.0,
                                references=[WindSpeedReference(height=80.0, shear=0.18)],
                            ),
                            WindSpeedHeightConfig(
                                height=160.0,
                                references=[WindSpeedReference(height=80.0, shear=0.18)],
                            ),
                        ]
                    ),
                    winddirection=WindDirectionConfig(heights=[]),
                ),
            ],
        )

        # M01 only needs 160m extrapolation
        assert len(config.masts[0].windspeed.heights) == 1
        assert config.masts[0].windspeed.heights[0].height == 160.0
        assert config.masts[0].windspeed.heights[0].references[0].shear == 0.15

        # M02 needs both 120m and 160m, with different shear
        assert len(config.masts[1].windspeed.heights) == 2
        assert config.masts[1].windspeed.heights[0].height == 120.0
        assert config.masts[1].windspeed.heights[0].references[0].shear == 0.18


class TestLoadExtrapolateConfig:
    """Tests for load_extrapolate_config function."""

    def test_load_from_toml(self, tmp_path: Path):
        """Test loading configuration from TOML file with per-mast structure."""
        toml_content = {
            "strategy": "top3-constant-shear",
            "masts": [
                {
                    "name": "M01",
                    "input": {"data": "./in/M01.csv", "sensors": "./in/M01.sensors.yaml"},
                    "output": {"data": "./out/M01.csv", "sensors": "./out/M01.sensors.yaml"},
                    "windspeed": {
                        "heights": [
                            {
                                "height": 160.0,
                                "references": [{"height": 100.0, "shear": 0.15, "weight": 1.0}],
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

        config_path = tmp_path / "vertical-extrapolate.toml"
        with open(config_path, "wb") as f:
            tomli_w.dump(toml_content, f)

        config = load_extrapolate_config(str(config_path))

        assert config.strategy == "top3-constant-shear"
        assert config.masts[0].name == "M01"
        assert config.masts[0].windspeed.heights[0].height == 160.0
