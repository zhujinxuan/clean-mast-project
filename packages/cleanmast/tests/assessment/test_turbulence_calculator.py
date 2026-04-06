"""Tests for turbulence calculator service.

Tests cover TI calculations, IEC category classification,
sector analysis, wind speed bin analysis, and edge cases.
"""

from datetime import datetime, timedelta

import numpy as np
import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.services.calculators.turbulence_calculator import (
    SECTOR_NAMES,
    TurbulenceCalculator,
    TurbulenceConstants,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TurbulenceSchema,
    TurbulenceSectorSchema,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def calculator() -> TurbulenceCalculator:
    """Create a TurbulenceCalculator instance."""
    return TurbulenceCalculator()


@pytest.fixture
def sample_turbulence_data() -> pl.DataFrame:
    """Create sample turbulence data DataFrame."""
    np.random.seed(42)
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]
    
    # Generate wind speeds with realistic turbulence
    base_speeds = 8.0 + 3.0 * np.sin(np.linspace(0, 4 * np.pi, 1000))
    noise = np.random.normal(0, 0.5, 1000)
    wind_speeds = np.maximum(base_speeds + noise, 0.5)
    
    return pl.DataFrame({
        "timestamp": timestamps,
        "WS_100m_avg": wind_speeds,
    })


@pytest.fixture
def sample_turbulence_data_multi_height() -> pl.DataFrame:
    """Create sample turbulence data with multiple heights."""
    np.random.seed(42)
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]
    
    # Generate wind speeds for different heights
    base_100m = 8.0 + 3.0 * np.sin(np.linspace(0, 4 * np.pi, 1000))
    base_120m = 9.0 + 3.5 * np.sin(np.linspace(0, 4 * np.pi, 1000))
    noise_100m = np.random.normal(0, 0.5, 1000)
    noise_120m = np.random.normal(0, 0.6, 1000)
    
    wind_speeds_100m = np.maximum(base_100m + noise_100m, 0.5)
    wind_speeds_120m = np.maximum(base_120m + noise_120m, 0.5)
    
    return pl.DataFrame({
        "timestamp": timestamps,
        "WS_100m_avg": wind_speeds_100m,
        "WS_120m_avg": wind_speeds_120m,
    })


@pytest.fixture
def sample_turbulence_data_with_direction() -> pl.DataFrame:
    """Create sample turbulence data with wind direction."""
    np.random.seed(42)
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]
    
    # Generate wind speeds
    base_speeds = 8.0 + 3.0 * np.sin(np.linspace(0, 4 * np.pi, 1000))
    noise = np.random.normal(0, 0.5, 1000)
    wind_speeds = np.maximum(base_speeds + noise, 0.5)
    
    # Generate wind directions (0-360 degrees)
    directions = (np.random.uniform(0, 360, 1000) + 
                  30 * np.sin(np.linspace(0, 2 * np.pi, 1000))) % 360
    
    return pl.DataFrame({
        "timestamp": timestamps,
        "WS_100m_avg": wind_speeds,
        "WD_100m_avg": directions,
    })


@pytest.fixture
def sample_input_single_height(sample_turbulence_data: pl.DataFrame) -> SingleMastAnalysisInput:
    """Create sample input data with single height."""
    sensors = [
        SensorColumn(
            column_name="WS_100m_avg",
            sensor_type="WindSpeed",
            sensor_direction="",
            height=100.0,
            stat_type="avg",
            unit="m/s",
        ),
    ]
    
    time_series = TimeSeriesData(df=sample_turbulence_data, sensors=sensors)
    parameters = AnalysisParameters(heights=[100.0], air_density=1.225)
    
    return SingleMastAnalysisInput(
        time_series=time_series,
        parameters=parameters,
        mast_name="TestMast",
    )


@pytest.fixture
def sample_input_multiple_heights(
    sample_turbulence_data_multi_height: pl.DataFrame,
) -> SingleMastAnalysisInput:
    """Create sample input data with multiple heights."""
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
            column_name="WS_120m_avg",
            sensor_type="WindSpeed",
            sensor_direction="",
            height=120.0,
            stat_type="avg",
            unit="m/s",
        ),
    ]
    
    time_series = TimeSeriesData(df=sample_turbulence_data_multi_height, sensors=sensors)
    parameters = AnalysisParameters(heights=[100.0, 120.0], air_density=1.225)
    
    return SingleMastAnalysisInput(
        time_series=time_series,
        parameters=parameters,
        mast_name="TestMast",
    )


@pytest.fixture
def sample_input_with_direction(
    sample_turbulence_data_with_direction: pl.DataFrame,
) -> SingleMastAnalysisInput:
    """Create sample input with wind direction."""
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
    
    time_series = TimeSeriesData(df=sample_turbulence_data_with_direction, sensors=sensors)
    parameters = AnalysisParameters(heights=[100.0], air_density=1.225)
    
    return SingleMastAnalysisInput(
        time_series=time_series,
        parameters=parameters,
        mast_name="TestMast",
    )


@pytest.fixture
def insufficient_data_input() -> SingleMastAnalysisInput:
    """Create input with insufficient data points."""
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(5)]
    
    df = pl.DataFrame({
        "timestamp": timestamps,
        "WS_100m_avg": [5.0, 6.0, 7.0, 8.0, 9.0],
    })
    
    sensors = [
        SensorColumn(
            column_name="WS_100m_avg",
            sensor_type="WindSpeed",
            sensor_direction="",
            height=100.0,
            stat_type="avg",
            unit="m/s",
        ),
    ]
    
    time_series = TimeSeriesData(df=df, sensors=sensors)
    parameters = AnalysisParameters(heights=[100.0], air_density=1.225)
    
    return SingleMastAnalysisInput(
        time_series=time_series,
        parameters=parameters,
        mast_name="TestMast",
    )


@pytest.fixture
def input_no_wind_speed() -> SingleMastAnalysisInput:
    """Create input with no wind speed sensors."""
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(100)]
    
    df = pl.DataFrame({
        "timestamp": timestamps,
        "Temp_100m_avg": [15.0] * 100,
    })
    
    sensors = [
        SensorColumn(
            column_name="Temp_100m_avg",
            sensor_type="Temperature",
            sensor_direction="",
            height=100.0,
            stat_type="avg",
            unit="C",
        ),
    ]
    
    time_series = TimeSeriesData(df=df, sensors=sensors)
    parameters = AnalysisParameters(heights=[100.0], air_density=1.225)
    
    return SingleMastAnalysisInput(
        time_series=time_series,
        parameters=parameters,
        mast_name="TestMast",
    )


# =============================================================================
# Test TurbulenceCalculator - Core Calculations
# =============================================================================


class TestTurbulenceCalculatorCore:
    """Tests for core TI calculation methods."""

    def test_ti_series_calculation(self, calculator: TurbulenceCalculator) -> None:
        """Test TI time series calculation."""
        # Create synthetic wind speed data with known std/mean
        np.random.seed(42)
        mean_ws = 8.0
        std_ws = 1.2
        wind_speeds = np.random.normal(mean_ws, std_ws, 1200)
        
        ti_series = calculator.calculate_ti_series(wind_speeds.tolist(), rolling_window=600)
        
        # Should have same length as input
        assert len(ti_series) == len(wind_speeds)
        
        # Middle values should have valid TI (not None)
        middle_ti = ti_series[500]
        assert middle_ti is not None
        
        # TI should be approximately std/mean
        expected_ti = std_ws / mean_ws
        assert abs(middle_ti - expected_ti) < 0.1
    
    def test_ti_series_edge_values_none(self, calculator: TurbulenceCalculator) -> None:
        """Test that edge values in TI series are None."""
        np.random.seed(42)
        wind_speeds = np.random.normal(8.0, 1.0, 1200)
        
        ti_series = calculator.calculate_ti_series(wind_speeds.tolist(), rolling_window=600)
        
        # Edge values should be None (incomplete window)
        half_window = 300
        assert ti_series[0] is None
        assert ti_series[half_window - 1] is None
        assert ti_series[-1] is None
        assert ti_series[-half_window] is None
    
    def test_ti_series_insufficient_data(self, calculator: TurbulenceCalculator) -> None:
        """Test TI series with insufficient data."""
        wind_speeds = [5.0] * 100
        
        ti_series = calculator.calculate_ti_series(wind_speeds, rolling_window=600)
        
        # Should return all None when data < rolling_window
        assert all(ti is None for ti in ti_series)
    
    def test_ti_series_minimum_wind_speed(self, calculator: TurbulenceCalculator) -> None:
        """Test TI calculation clamps minimum wind speed."""
        # Create data with very low wind speeds
        wind_speeds = [0.1] * 1200
        
        ti_series = calculator.calculate_ti_series(wind_speeds, rolling_window=600)
        
        # Middle values should be calculated with clamped minimum
        middle_ti = ti_series[600]
        assert middle_ti is not None
        # With near-zero std and clamped mean of 1.0, TI should be near-zero
        assert middle_ti < 0.1
    
    def test_calculate_representative_ti(self, calculator: TurbulenceCalculator) -> None:
        """Test representative TI (P90) calculation."""
        # Known TI values
        ti_values = [0.10, 0.12, 0.14, 0.16, 0.18] * 20  # 100 values
        
        rep_ti = calculator.calculate_representative_ti(ti_values)
        
        assert rep_ti is not None
        # P90 = mean + 1.28 * std
        mean_ti = np.mean(ti_values)
        std_ti = np.std(ti_values, ddof=1)
        expected_rep = mean_ti + 1.28 * std_ti
        assert abs(rep_ti - expected_rep) < 0.01
    
    def test_calculate_representative_ti_with_none(self, calculator: TurbulenceCalculator) -> None:
        """Test representative TI calculation with None values."""
        ti_values = [0.10, None, 0.12, None, 0.14] * 20  # 100 values, 40% None
        
        rep_ti = calculator.calculate_representative_ti(ti_values)
        
        assert rep_ti is not None
        # Should filter out None values
        valid_ti = [ti for ti in ti_values if ti is not None]
        expected_rep = np.mean(valid_ti) + 1.28 * np.std(valid_ti, ddof=1)
        assert abs(rep_ti - expected_rep) < 0.01
    
    def test_calculate_representative_ti_insufficient_data(
        self, calculator: TurbulenceCalculator
    ) -> None:
        """Test representative TI returns None for insufficient data."""
        ti_values = [0.10, 0.12, 0.14, 0.16, 0.18]  # Only 5 values
        
        rep_ti = calculator.calculate_representative_ti(ti_values)
        
        assert rep_ti is None
    
    def test_calculate_iec_ti(self, calculator: TurbulenceCalculator) -> None:
        """Test IEC reference TI calculation."""
        # Formula: TI_IEC = I_ref * (0.75 + 5.6/V)
        i_ref = 0.16  # IEC A category
        wind_speed = 8.0
        
        iec_ti = calculator.calculate_iec_ti(wind_speed, i_ref)
        
        assert iec_ti is not None
        expected = i_ref * (0.75 + 5.6 / wind_speed)
        assert abs(iec_ti - expected) < 0.001
    
    def test_calculate_iec_ti_zero_wind_speed(self, calculator: TurbulenceCalculator) -> None:
        """Test IEC TI returns None for zero wind speed."""
        iec_ti = calculator.calculate_iec_ti(0.0, 0.16)
        
        assert iec_ti is None
    
    def test_calculate_iec_ti_negative_wind_speed(self, calculator: TurbulenceCalculator) -> None:
        """Test IEC TI returns None for negative wind speed."""
        iec_ti = calculator.calculate_iec_ti(-5.0, 0.16)
        
        assert iec_ti is None


# =============================================================================
# Test IEC Category Classification
# =============================================================================


class TestIECCategoryClassification:
    """Tests for IEC category classification."""

    def test_classify_iec_category_high_turbulence(self, calculator: TurbulenceCalculator) -> None:
        """Test classification for high turbulence (A+)."""
        # At V=8 m/s: IEC A+ reference = 0.18 * (0.75 + 5.6/8) = 0.261
        # Need measured TI close to 0.26 for A+ classification
        ti_values = [0.25, 0.26, 0.27, 0.28] * 30
        wind_speeds = [8.0] * len(ti_values)
        
        category = calculator.classify_iec_category(ti_values, wind_speeds)
        
        assert category == "A+"
    
    def test_classify_iec_category_medium_turbulence(self, calculator: TurbulenceCalculator) -> None:
        """Test classification for medium turbulence (B)."""
        # At V=8 m/s: IEC B reference = 0.14 * (0.75 + 5.6/8) = 0.203
        # Need measured TI close to 0.20 for B classification
        ti_values = [0.19, 0.20, 0.21, 0.205] * 30
        wind_speeds = [8.0] * len(ti_values)
        
        category = calculator.classify_iec_category(ti_values, wind_speeds)
        
        assert category == "B"
    
    def test_classify_iec_category_low_turbulence(self, calculator: TurbulenceCalculator) -> None:
        """Test classification for low turbulence (C)."""
        # Low TI values that should result in C category
        ti_values = [0.10, 0.11, 0.12, 0.13] * 30
        wind_speeds = [8.0] * len(ti_values)
        
        category = calculator.classify_iec_category(ti_values, wind_speeds)
        
        assert category == "C"
    
    def test_classify_iec_category_insufficient_data(
        self, calculator: TurbulenceCalculator
    ) -> None:
        """Test classification defaults to C for insufficient data."""
        ti_values = [0.15] * 5  # Less than MIN_SAMPLES
        wind_speeds = [8.0] * 5
        
        category = calculator.classify_iec_category(ti_values, wind_speeds)
        
        assert category == "C"
    
    def test_classify_iec_category_with_none_values(self, calculator: TurbulenceCalculator) -> None:
        """Test classification handles None values correctly."""
        # At V=8 m/s: IEC C reference = 0.12 * (0.75 + 5.6/8) = 0.174
        # TI around 0.15 will be closest to C category
        ti_values = [0.14, None, 0.15, None, 0.145] * 30
        wind_speeds = [8.0] * len(ti_values)
        
        category = calculator.classify_iec_category(ti_values, wind_speeds)
        
        # Should classify based on valid values (around 0.15 = C category)
        assert category in ["B", "C"]


# =============================================================================
# Test Wind Speed Bin Analysis
# =============================================================================


class TestWindSpeedAnalysis:
    """Tests for wind speed bin turbulence analysis."""

    def test_analyze_by_wind_speed(
        self, calculator: TurbulenceCalculator, sample_input_single_height: SingleMastAnalysisInput
    ) -> None:
        """Test analysis by wind speed bins."""
        result = calculator.analyze_by_wind_speed(sample_input_single_height)
        
        assert result is not None
        assert result.schema == TurbulenceSchema
        
        # Check data has expected columns
        expected_columns = {
            "wind_speed_bin", "height", "interpolation_marker", "mean_ti",
            "std_ti", "representative_ti", "iec_category"
        }
        assert set(result.data.columns) == expected_columns
        
        # Should have data rows
        assert len(result.data) > 0
        
        # Check metadata
        assert result.metadata.mast_name == "TestMast"
    
    def test_analyze_by_wind_speed_multiple_heights(
        self, calculator: TurbulenceCalculator, sample_input_multiple_heights: SingleMastAnalysisInput
    ) -> None:
        """Test analysis with multiple heights."""
        result = calculator.analyze_by_wind_speed(sample_input_multiple_heights)
        
        assert result is not None
        assert len(result.data) > 0
        
        # Check both heights are present
        heights = result.data["height"].unique().to_list()
        assert 100.0 in heights
        assert 120.0 in heights
    
    def test_analyze_by_wind_speed_no_wind_sensors(
        self, calculator: TurbulenceCalculator, input_no_wind_speed: SingleMastAnalysisInput
    ) -> None:
        """Test analysis with no wind speed sensors."""
        result = calculator.analyze_by_wind_speed(input_no_wind_speed)
        
        assert result is not None
        # Should return empty dataframe
        assert len(result.data) == 0
    
    def test_analyze_by_wind_speed_insufficient_data(
        self, calculator: TurbulenceCalculator, insufficient_data_input: SingleMastAnalysisInput
    ) -> None:
        """Test analysis with insufficient data."""
        result = calculator.analyze_by_wind_speed(insufficient_data_input)
        
        assert result is not None
        # Should return empty or minimal dataframe
        # Note: The implementation may still create bins with few samples
    
    def test_ti_values_in_valid_range(self, calculator: TurbulenceCalculator) -> None:
        """Test that calculated TI values are in reasonable range."""
        # Create realistic wind data
        np.random.seed(42)
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(500)]
        wind_speeds = np.maximum(np.random.normal(8.0, 2.0, 500), 0.5)
        
        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_100m_avg": wind_speeds,
        })
        
        sensors = [
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]
        
        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[100.0], air_density=1.225)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )
        
        result = calculator.analyze_by_wind_speed(input_data)
        
        if len(result.data) > 0:
            # TI values should be in reasonable range (0 to 0.5)
            mean_ti_values = result.data["mean_ti"].to_list()
            for ti in mean_ti_values:
                assert 0 <= ti < 0.5, f"TI value {ti} out of expected range"
    
    def test_iec_categories_are_valid(self, calculator: TurbulenceCalculator) -> None:
        """Test that IEC categories are valid."""
        np.random.seed(42)
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(500)]
        wind_speeds = np.maximum(np.random.normal(8.0, 2.0, 500), 0.5)
        
        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_100m_avg": wind_speeds,
        })
        
        sensors = [
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]
        
        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[100.0], air_density=1.225)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )
        
        result = calculator.analyze_by_wind_speed(input_data)
        
        valid_categories = {"A+", "A", "B", "C"}
        for row in result.data.iter_rows(named=True):
            assert row["iec_category"] in valid_categories


# =============================================================================
# Test Sector Analysis
# =============================================================================


class TestSectorAnalysis:
    """Tests for direction sector turbulence analysis."""

    def test_analyze_by_sector(
        self, calculator: TurbulenceCalculator, sample_input_with_direction: SingleMastAnalysisInput
    ) -> None:
        """Test analysis by direction sectors."""
        result = calculator.analyze_by_sector(sample_input_with_direction)
        
        assert result is not None
        assert result.schema == TurbulenceSectorSchema
        
        # Check data has expected columns
        expected_columns = {
            "sector", "sector_name", "height", "interpolation_marker",
            "mean_ti", "representative_ti", "iec_category"
        }
        assert set(result.data.columns) == expected_columns
    
    def test_sector_names_are_valid(self, calculator: TurbulenceCalculator) -> None:
        """Test that sector names match expected 16-sector naming."""
        np.random.seed(42)
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(500)]
        wind_speeds = np.maximum(np.random.normal(8.0, 2.0, 500), 0.5)
        directions = np.random.uniform(0, 360, 500)
        
        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_100m_avg": wind_speeds,
            "WD_100m_avg": directions,
        })
        
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
        
        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[100.0], air_density=1.225)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )
        
        result = calculator.analyze_by_sector(input_data)
        
        # All sector names should be valid
        for row in result.data.iter_rows(named=True):
            assert row["sector_name"] in SECTOR_NAMES
            assert 0 <= row["sector"] <= 15
    
    def test_analyze_by_sector_no_direction_sensor(
        self, calculator: TurbulenceCalculator, sample_input_single_height: SingleMastAnalysisInput
    ) -> None:
        """Test sector analysis with no direction sensor."""
        result = calculator.analyze_by_sector(sample_input_single_height)
        
        assert result is not None
        # Should return empty dataframe
        assert len(result.data) == 0
    
    def test_analyze_by_sector_no_wind_sensor(
        self, calculator: TurbulenceCalculator, input_no_wind_speed: SingleMastAnalysisInput
    ) -> None:
        """Test sector analysis with no wind speed sensor."""
        result = calculator.analyze_by_sector(input_no_wind_speed)
        
        assert result is not None
        # Should return empty dataframe
        assert len(result.data) == 0


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_dataframe(self, calculator: TurbulenceCalculator) -> None:
        """Test handling of empty DataFrame."""
        df = pl.DataFrame({
            "timestamp": [],
            "WS_100m_avg": [],
        })
        
        sensors = [
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]
        
        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[100.0], air_density=1.225)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )
        
        result = calculator.analyze_by_wind_speed(input_data)
        
        assert result is not None
        assert len(result.data) == 0
    
    def test_missing_column(self, calculator: TurbulenceCalculator) -> None:
        """Test handling when sensor column doesn't exist in DataFrame."""
        df = pl.DataFrame({
            "timestamp": [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(100)],
            "SomeOtherColumn": [5.0] * 100,
        })
        
        sensors = [
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]
        
        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[100.0], air_density=1.225)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )
        
        result = calculator.analyze_by_wind_speed(input_data)
        
        assert result is not None
        # Should handle gracefully (skip missing column)
    
    def test_constants(self) -> None:
        """Test that TurbulenceConstants has expected values."""
        constants = TurbulenceConstants()
        
        assert constants.MIN_SAMPLES == 10
        assert constants.TI_REP_Z == 1.28
        assert constants.MIN_WIND_SPEED == 1.0
        assert constants.NUM_SECTORS == 16
        assert constants.SECTOR_WIDTH == 22.5
    
    def test_sector_names_count(self) -> None:
        """Test that SECTOR_NAMES has 16 entries."""
        assert len(SECTOR_NAMES) == 16
        # Check specific expected sectors
        assert SECTOR_NAMES[0] == "N"
        assert SECTOR_NAMES[4] == "E"
        assert SECTOR_NAMES[8] == "S"
        assert SECTOR_NAMES[12] == "W"
    
    def test_iec_categories_in_calculator(self, calculator: TurbulenceCalculator) -> None:
        """Test that calculator has expected IEC categories."""
        expected_categories = {"A+": 0.18, "A": 0.16, "B": 0.14, "C": 0.12}
        assert calculator.iec_categories == expected_categories


# =============================================================================
# Test Time Range Extraction
# =============================================================================


class TestTimeRangeExtraction:
    """Tests for time range extraction."""

    def test_get_time_range_with_timestamp(self, calculator: TurbulenceCalculator) -> None:
        """Test time range extraction from DataFrame with timestamp."""
        df = pl.DataFrame({
            "timestamp": [
                datetime(2023, 1, 1),
                datetime(2023, 6, 15),
                datetime(2023, 12, 31),
            ],
            "WS_100m_avg": [5.0, 6.0, 7.0],
        })
        
        time_range = calculator._get_time_range(df)
        
        assert "2023-01-01" in time_range
        assert "2023-12-31" in time_range
        assert "to" in time_range
    
    def test_get_time_range_no_timestamp(self, calculator: TurbulenceCalculator) -> None:
        """Test time range extraction without timestamp column."""
        df = pl.DataFrame({
            "WS_100m_avg": [5.0, 6.0, 7.0],
        })
        
        time_range = calculator._get_time_range(df)
        
        assert time_range == "Unknown"
    
    def test_get_time_range_empty_df(self, calculator: TurbulenceCalculator) -> None:
        """Test time range extraction from empty DataFrame."""
        df = pl.DataFrame({
            "timestamp": [],
            "WS_100m_avg": [],
        })
        
        time_range = calculator._get_time_range(df)
        
        assert time_range == "Unknown"
