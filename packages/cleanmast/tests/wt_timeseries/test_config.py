"""Tests for wt_timeseries configuration module."""


import pytest
from cleanmast.shared.timeseries.time_series_source import TimeSeriesSource
from cleanmast.subdomains.configuration import WtTimeSeriesConfiguration, WtTimeSeriesMast
from pydantic import ValidationError


class TestWtTimeSeriesMast:
    """Tests for WtTimeSeriesMast validation."""

    def test_valid_mast_creation(self):
        """Test creating a valid WtTimeSeriesMast."""
        mast = WtTimeSeriesMast(
            name="TGL1",
            input=TimeSeriesSource(data="./data.parquet"),
            csv_heights=[100.0, 120.0, 140.0],
            turbulence_heights=[80.0, 100.0],
        )
        assert mast.name == "TGL1"
        assert mast.csv_heights == [100.0, 120.0, 140.0]
        assert mast.turbulence_heights == [80.0, 100.0]

    def test_csv_heights_minimum_100(self):
        """Test that csv_heights must be >= 100.0."""
        # Should raise ValidationError for height < 100
        with pytest.raises(ValidationError) as exc_info:
            WtTimeSeriesMast(
                name="TGL1",
                input=TimeSeriesSource(data="./data.parquet"),
                csv_heights=[80.0, 100.0, 120.0],
                turbulence_heights=[80.0],
            )
        assert "csv_heights must be >= 100.0" in str(exc_info.value)

    def test_csv_heights_exactly_100_allowed(self):
        """Test that height exactly 100.0 is allowed."""
        mast = WtTimeSeriesMast(
            name="TGL1",
            input=TimeSeriesSource(data="./data.parquet"),
            csv_heights=[100.0],
            turbulence_heights=[80.0],
        )
        assert mast.csv_heights == [100.0]

    def test_empty_csv_heights_allowed(self):
        """Test that empty csv_heights list is allowed."""
        mast = WtTimeSeriesMast(
            name="TGL1",
            input=TimeSeriesSource(data="./data.parquet"),
            csv_heights=[],
            turbulence_heights=[80.0, 100.0],
        )
        assert mast.csv_heights == []

    def test_negative_csv_height_rejected(self):
        """Test that negative csv_heights are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            WtTimeSeriesMast(
                name="TGL1",
                input=TimeSeriesSource(data="./data.parquet"),
                csv_heights=[-10.0, 100.0],
                turbulence_heights=[80.0],
            )
        assert "csv_heights must be >= 100.0" in str(exc_info.value)

    def test_zero_csv_height_rejected(self):
        """Test that zero csv_heights are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            WtTimeSeriesMast(
                name="TGL1",
                input=TimeSeriesSource(data="./data.parquet"),
                csv_heights=[0.0, 100.0],
                turbulence_heights=[80.0],
            )
        assert "csv_heights must be >= 100.0" in str(exc_info.value)


class TestWtTimeSeriesConfiguration:
    """Tests for WtTimeSeriesConfiguration validation."""

    def test_valid_configuration(self):
        """Test creating a valid configuration."""
        config = WtTimeSeriesConfiguration(
            masts=[
                WtTimeSeriesMast(
                    name="TGL1",
                    input=TimeSeriesSource(data="./data.parquet"),
                    csv_heights=[100.0, 120.0],
                    turbulence_heights=[80.0],
                ),
                WtTimeSeriesMast(
                    name="TGL2",
                    input=TimeSeriesSource(data="./data2.parquet"),
                    csv_heights=[100.0],
                    turbulence_heights=[80.0],
                ),
            ]
        )
        assert len(config.masts) == 2
        assert config.masts[0].name == "TGL1"
        assert config.masts[1].name == "TGL2"

    def test_duplicate_mast_names_rejected(self):
        """Test that duplicate mast names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            WtTimeSeriesConfiguration(
                masts=[
                    WtTimeSeriesMast(
                        name="TGL1",
                        input=TimeSeriesSource(data="./data.parquet"),
                        csv_heights=[100.0],
                        turbulence_heights=[80.0],
                    ),
                    WtTimeSeriesMast(
                        name="TGL1",
                        input=TimeSeriesSource(data="./data2.parquet"),
                        csv_heights=[120.0],
                        turbulence_heights=[100.0],
                    ),
                ]
            )
        assert "Duplicate mast names found" in str(exc_info.value)

    def test_empty_masts_list_allowed(self):
        """Test that empty masts list is allowed."""
        config = WtTimeSeriesConfiguration(masts=[])
        assert config.masts == []

    def test_single_mast_configuration(self):
        """Test configuration with single mast."""
        config = WtTimeSeriesConfiguration(
            masts=[
                WtTimeSeriesMast(
                    name="TGL1",
                    input=TimeSeriesSource(data="./data.parquet"),
                    csv_heights=[100.0, 120.0, 140.0],
                    turbulence_heights=[80.0, 100.0, 120.0],
                ),
            ]
        )
        assert len(config.masts) == 1
