"""Tests for report configuration models."""

import tempfile
from pathlib import Path

import tomli_w
from cleanmast.subdomains.assessment.domain.value_objects import (
    MastConfig,
    RepTsReportConfig,
)
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)


class TestMastConfig:
    """Tests for MastConfig model."""
    
    def test_valid_config(self):
        """Test creating valid MastConfig."""
        config = MastConfig(
            name="M6002",
            air_density=1.225,
            input=TimeSeriesSource(data="./data.parquet")
        )
        
        assert config.name == "M6002"
        assert config.air_density == 1.225
        assert isinstance(config.input, TimeSeriesSource)
        assert config.input.data == "./data.parquet"
    
    def test_time_series_source_validation(self):
        """Test that input is validated as TimeSeriesSource."""
        config = MastConfig(
            name="M9773",
            air_density=1.003,
            input=TimeSeriesSource(data="./data.parquet")
        )
        assert config.input.data == "./data.parquet"
        assert config.input.sensors is None  # Optional for Parquet


class TestRepTsReportConfig:
    """Tests for RepTsReportConfig model."""
    
    def test_from_toml(self):
        """Test loading config from TOML file."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            tomli_w.dump({
                "masts": [
                    {
                        "name": "M6002",
                        "air_density": 1.225,
                        "input": {"data": "./data.parquet"}
                    }
                ]
            }, f)
            f.flush()
            
            config = RepTsReportConfig.from_toml(Path(f.name))
            
            assert len(config.masts) == 1
            assert config.masts[0].name == "M6002"
            assert isinstance(config.masts[0].input, TimeSeriesSource)
    
    def test_multiple_masts(self):
        """Test config with multiple masts."""
        config = RepTsReportConfig(
            masts=[
                MastConfig(name="M6002", air_density=1.225, input=TimeSeriesSource(data="./m1.parquet")),
                MastConfig(name="M9773", air_density=1.003, input=TimeSeriesSource(data="./m2.parquet")),
            ]
        )
        
        assert len(config.masts) == 2
        assert config.masts[0].name == "M6002"
        assert config.masts[1].name == "M9773"
