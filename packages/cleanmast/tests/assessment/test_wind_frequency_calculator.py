"""Tests for wind frequency calculator service.

Tests cover histogram calculations, power frequency calculations,
range summaries, and edge cases.
"""

from datetime import datetime, timedelta

import numpy as np
import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.services.calculators.wind_frequency_calculator import (
    WindFrequencyCalculator,
    WindFrequencyConstants,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WindFrequencySchema,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


@pytest.fixture
def calculator() -> WindFrequencyCalculator:
    """Create a WindFrequencyCalculator instance."""
    return WindFrequencyCalculator()


@pytest.fixture
def sample_wind_data() -> pl.DataFrame:
    """Create sample wind speed data DataFrame."""
    np.random.seed(42)
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]
    
    # Generate wind speeds with realistic distribution (Weibull-like)
    wind_speeds = np.random.weibull(2, 1000) * 8.0  # Shape=2, scale=8
    wind_speeds = np.clip(wind_speeds, 0, 35)  # Cap at 35 m/s
    
    return pl.DataFrame({
        "timestamp": timestamps,
        "WS_100m_avg": wind_speeds,
    })


@pytest.fixture
def sample_wind_data_multi_height() -> pl.DataFrame:
    """Create sample wind data with multiple heights."""
    np.random.seed(42)
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]
    
    # Different wind speeds for different heights (higher = faster)
    wind_speeds_100m = np.random.weibull(2, 1000) * 8.0
    wind_speeds_120m = np.random.weibull(2, 1000) * 9.0
    wind_speeds_140m = np.random.weibull(2, 1000) * 10.0
    
    return pl.DataFrame({
        "timestamp": timestamps,
        "WS_100m_avg": np.clip(wind_speeds_100m, 0, 35),
        "WS_120m_avg": np.clip(wind_speeds_120m, 0, 35),
        "WS_140m_avg": np.clip(wind_speeds_140m, 0, 35),
    })


@pytest.fixture
def sample_input_single_height(sample_wind_data: pl.DataFrame) -> SingleMastAnalysisInput:
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
    
    time_series = TimeSeriesData(df=sample_wind_data, sensors=sensors)
    parameters = AnalysisParameters(heights=[100.0], air_density=1.225)
    
    return SingleMastAnalysisInput(
        time_series=time_series,
        parameters=parameters,
        mast_name="TestMast",
    )


@pytest.fixture
def sample_input_multiple_heights(
    sample_wind_data_multi_height: pl.DataFrame,
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
        SensorColumn(
            column_name="WS_140m_avg",
            sensor_type="WindSpeed",
            sensor_direction="",
            height=140.0,
            stat_type="avg",
            unit="m/s",
        ),
    ]
    
    time_series = TimeSeriesData(df=sample_wind_data_multi_height, sensors=sensors)
    parameters = AnalysisParameters(heights=[100.0, 120.0, 140.0], air_density=1.225)
    
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


@pytest.fixture
def known_wind_speeds() -> list[float]:
    """Create known wind speeds for predictable tests."""
    # Create wind speeds that fall into specific bins
    # Bins: [0,1), [1,2), [2,3), [3,4), [4,5), etc.
    return [
        # 10 values in [0,1)
        0.5, 0.6, 0.7, 0.8, 0.9, 0.1, 0.2, 0.3, 0.4, 0.55,
        # 20 values in [1,2)
        1.5, 1.6, 1.7, 1.8, 1.9, 1.1, 1.2, 1.3, 1.4, 1.55,
        1.51, 1.61, 1.71, 1.81, 1.91, 1.11, 1.21, 1.31, 1.41, 1.52,
        # 30 values in [2,3)
        2.5, 2.6, 2.7, 2.8, 2.9, 2.1, 2.2, 2.3, 2.4, 2.55,
        2.51, 2.61, 2.71, 2.81, 2.91, 2.11, 2.21, 2.31, 2.41, 2.52,
        2.53, 2.63, 2.73, 2.83, 2.93, 2.13, 2.23, 2.33, 2.43, 2.56,
        # 40 values in [3,4)
        3.5, 3.6, 3.7, 3.8, 3.9, 3.1, 3.2, 3.3, 3.4, 3.55,
        3.51, 3.61, 3.71, 3.81, 3.91, 3.11, 3.21, 3.31, 3.41, 3.52,
        3.53, 3.63, 3.73, 3.83, 3.93, 3.13, 3.23, 3.33, 3.43, 3.56,
        3.57, 3.67, 3.77, 3.87, 3.97, 3.17, 3.27, 3.37, 3.47, 3.58,
    ]


class TestWindFrequencyCalculatorCore:
    """Tests for core frequency calculation methods."""

    def test_calculate_histogram(self, calculator: WindFrequencyCalculator) -> None:
        """Test histogram calculation with known values."""
        wind_speeds = [
            0.5, 0.6, 0.7,  # 3 values in bin 0
            1.5, 1.6,       # 2 values in bin 1
            2.5, 2.6, 2.7,  # 3 values in bin 2
        ]
        
        histogram = calculator.calculate_histogram(wind_speeds)
        
        assert histogram[0] == 3
        assert histogram[1] == 2
        assert histogram[2] == 3
    
    def test_calculate_histogram_empty(self, calculator: WindFrequencyCalculator) -> None:
        """Test histogram with empty data."""
        histogram = calculator.calculate_histogram([])
        
        assert histogram == {}
    
    def test_calculate_histogram_boundary_values(self, calculator: WindFrequencyCalculator) -> None:
        """Test histogram boundary handling."""
        # Test exact boundaries
        wind_speeds = [
            0.0,   # Should be in bin 0
            0.999, # Should be in bin 0
            1.0,   # Should be in bin 1
            1.999, # Should be in bin 1
            28.0,  # Should be in bin 28 (capped)
            35.0,  # Should be in bin 28 (capped)
        ]
        
        histogram = calculator.calculate_histogram(wind_speeds)
        
        assert histogram[0] == 2  # 0.0, 0.999
        assert histogram[1] == 2  # 1.0, 1.999
        assert histogram[28] == 2  # 28.0, 35.0 (capped)
    
    def test_calculate_histogram_max_bin(self, calculator: WindFrequencyCalculator) -> None:
        """Test that values above MAX_BIN are capped."""
        wind_speeds = [30.0, 35.0, 40.0, 50.0]
        
        histogram = calculator.calculate_histogram(wind_speeds)
        
        # All should be in bin 28 (capped at MAX_BIN)
        assert histogram[28] == 4
    
    def test_calculate_power_frequency(self, calculator: WindFrequencyCalculator) -> None:
        """Test power frequency calculation."""
        wind_speeds = [2.0, 4.0, 6.0, 8.0]
        
        power_freq = calculator.calculate_power_frequency(wind_speeds)
        
        assert power_freq[2] == pytest.approx(0.01, abs=0.01)
        assert power_freq[4] == pytest.approx(0.08, abs=0.01)
        assert power_freq[6] == pytest.approx(0.27, abs=0.01)
        assert power_freq[8] == pytest.approx(0.64, abs=0.01)
    
    def test_calculate_power_frequency_empty(self, calculator: WindFrequencyCalculator) -> None:
        """Test power frequency with empty data."""
        power_freq = calculator.calculate_power_frequency([])
        
        assert power_freq == {}
    
    def test_calculate_power_frequency_custom_air_density(
        self, calculator: WindFrequencyCalculator
    ) -> None:
        """Test power frequency with custom air density."""
        wind_speeds = [5.0, 10.0]
        
        # With default density (1.225)
        power_freq_default = calculator.calculate_power_frequency(wind_speeds)
        
        # With custom density (1.5) - ratios should be same
        power_freq_custom = calculator.calculate_power_frequency(wind_speeds, air_density=1.5)
        
        # Power frequency ratios should be independent of air density
        assert power_freq_default[5] == pytest.approx(power_freq_custom[5], abs=0.0001)
        assert power_freq_default[10] == pytest.approx(power_freq_custom[10], abs=0.0001)
    
    def test_calculate_power_frequency_all_zero_wind_speed(
        self, calculator: WindFrequencyCalculator
    ) -> None:
        """Test power frequency with zero wind speeds."""
        wind_speeds = [0.0, 0.0, 0.0]
        
        power_freq = calculator.calculate_power_frequency(wind_speeds)
        
        # All power is zero, so should return empty dict
        assert power_freq == {}

    def test_calculate_air_density(self, calculator: WindFrequencyCalculator) -> None:
        """Test air density calculation matches Julia barometric formula."""
        # Julia barometric formula:
        # T = 288.15 - 0.0065 * height
        # ratio = (T / 288.15)^(9.81 / (287.05 * 0.0065))
        # rho = 1.225 * ratio
        rho_120 = calculator.calculate_air_density(120.0)
        rho_160 = calculator.calculate_air_density(160.0)

        assert rho_120 == pytest.approx(1.2076656476755538, rel=1e-9)
        assert rho_160 == pytest.approx(1.2019318778832613, rel=1e-9)
    
    def test_calculate_range_summary(self, calculator: WindFrequencyCalculator) -> None:
        """Test range summary calculation."""
        # Wind speeds: 10 values in [3,25), 10 values outside
        wind_speeds = [
            5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0,  # In range
            1.0, 1.5, 2.0, 2.5, 26.0, 27.0, 28.0, 29.0, 30.0, 0.5,   # Out of range
        ]
        
        summary = calculator.calculate_range_summary(wind_speeds, min_speed=3.0, max_speed=25.0)
        
        assert summary["count"] == 10.0
        assert summary["frequency"] == pytest.approx(0.5, abs=0.01)
        assert summary["occurrence_hours"] == pytest.approx(4380.0, abs=10.0)  # 0.5 * 8760
        assert summary["mean_speed"] == pytest.approx(9.5, abs=0.1)
    
    def test_calculate_range_summary_default_range(
        self, calculator: WindFrequencyCalculator
    ) -> None:
        """Test range summary with default productive range (3~25 m/s)."""
        wind_speeds = [2.0, 5.0, 10.0, 20.0, 30.0]  # 3 in range [3,25), 2 outside
        
        summary = calculator.calculate_range_summary(wind_speeds)
        
        assert summary["count"] == 3.0  # 5.0, 10.0, 20.0
    
    def test_calculate_range_summary_empty(self, calculator: WindFrequencyCalculator) -> None:
        """Test range summary with empty data."""
        summary = calculator.calculate_range_summary([])
        
        assert summary["count"] == 0.0
        assert summary["frequency"] == 0.0
        assert summary["mean_speed"] == 0.0
        assert summary["mean_power"] == 0.0
        assert summary["occurrence_hours"] == 0.0
    
    def test_calculate_range_summary_no_data_in_range(
        self, calculator: WindFrequencyCalculator
    ) -> None:
        """Test range summary when no data falls in range."""
        wind_speeds = [1.0, 2.0, 26.0, 27.0]  # All outside [3,25)
        
        summary = calculator.calculate_range_summary(wind_speeds, min_speed=3.0, max_speed=25.0)
        
        assert summary["count"] == 0.0
        assert summary["frequency"] == 0.0


class TestWindFrequencyAnalysis:
    """Tests for wind frequency analysis by height."""

    def test_analyze_by_height(
        self, calculator: WindFrequencyCalculator, sample_input_single_height: SingleMastAnalysisInput
    ) -> None:
        """Test frequency analysis for single height."""
        result = calculator.analyze_by_height(sample_input_single_height)
        
        assert result is not None
        assert result.schema == WindFrequencySchema
        
        # Check data has expected columns
        expected_columns = {
            "height", "interpolation_marker", "bin_start", "bin_end",
            "bin_center", "frequency", "occurrence_hours",
            "power_frequency", "power_hours"
        }
        assert set(result.data.columns) == expected_columns
        
        # Should have data rows
        assert len(result.data) > 0
        
        # Check metadata
        assert result.metadata.mast_name == "TestMast"
    
    def test_analyze_by_height_frequency_sums_to_one(
        self, calculator: WindFrequencyCalculator, sample_input_single_height: SingleMastAnalysisInput
    ) -> None:
        """Test that frequency sums to 1.0 for each height."""
        result = calculator.analyze_by_height(sample_input_single_height)
        
        if len(result.data) > 0:
            total_frequency = result.data["frequency"].sum()
            assert total_frequency == pytest.approx(1.0, abs=0.01)
    
    def test_analyze_by_height_power_frequency_sums_to_one(
        self, calculator: WindFrequencyCalculator, sample_input_single_height: SingleMastAnalysisInput
    ) -> None:
        """Test that power frequency sums to 1.0 for each height."""
        result = calculator.analyze_by_height(sample_input_single_height)
        
        if len(result.data) > 0:
            total_power_frequency = result.data["power_frequency"].sum()
            assert total_power_frequency == pytest.approx(1.0, abs=0.01)
    
    def test_analyze_by_height_occurrence_hours_calculation(
        self, calculator: WindFrequencyCalculator, sample_input_single_height: SingleMastAnalysisInput
    ) -> None:
        """Test that occurrence_hours = int(round(frequency * 8760))."""
        result = calculator.analyze_by_height(sample_input_single_height)

        if len(result.data) > 0:
            for row in result.data.iter_rows(named=True):
                expected_hours = int(round(row["frequency"] * 8760.0))
                assert row["occurrence_hours"] == expected_hours

    def test_analyze_by_height_power_hours_calculation(
        self, calculator: WindFrequencyCalculator, sample_input_single_height: SingleMastAnalysisInput
    ) -> None:
        """Test that power_hours = int(round(power_frequency * 8760))."""
        result = calculator.analyze_by_height(sample_input_single_height)

        if len(result.data) > 0:
            for row in result.data.iter_rows(named=True):
                expected_hours = int(round(row["power_frequency"] * 8760.0))
                assert row["power_hours"] == expected_hours
    
    def test_analyze_by_height_multiple_heights(
        self, calculator: WindFrequencyCalculator, sample_input_multiple_heights: SingleMastAnalysisInput
    ) -> None:
        """Test analysis with multiple heights."""
        result = calculator.analyze_by_height(sample_input_multiple_heights)
        
        assert result is not None
        assert len(result.data) > 0
        
        # Check all heights are present
        heights = result.data["height"].unique().to_list()
        assert 100.0 in heights
        assert 120.0 in heights
        assert 140.0 in heights
    
    def test_analyze_by_height_no_wind_sensors(
        self, calculator: WindFrequencyCalculator, input_no_wind_speed: SingleMastAnalysisInput
    ) -> None:
        """Test analysis with no wind speed sensors."""
        result = calculator.analyze_by_height(input_no_wind_speed)
        
        assert result is not None
        # Should return empty dataframe
        assert len(result.data) == 0
    
    def test_analyze_by_height_insufficient_data(
        self, calculator: WindFrequencyCalculator, insufficient_data_input: SingleMastAnalysisInput
    ) -> None:
        """Test analysis with insufficient data."""
        result = calculator.analyze_by_height(insufficient_data_input)
        
        assert result is not None
        # Should return empty dataframe (less than MIN_SAMPLES)
        assert len(result.data) == 0


class TestFrequencyConstraints:
    """Tests for frequency sum constraints."""

    def test_frequency_sum_constraint_known_data(
        self, calculator: WindFrequencyCalculator, known_wind_speeds: list[float]
    ) -> None:
        """Test frequency sums to 1.0 with known data."""
        histogram = calculator.calculate_histogram(known_wind_speeds)
        total_count = sum(histogram.values())
        
        # Calculate frequencies
        frequencies = {k: v / total_count for k, v in histogram.items()}
        
        # Sum should be 1.0
        total_frequency = sum(frequencies.values())
        assert total_frequency == pytest.approx(1.0, abs=0.0001)
    
    def test_power_frequency_sum_constraint_known_data(
        self, calculator: WindFrequencyCalculator, known_wind_speeds: list[float]
    ) -> None:
        """Test power frequency sums to 1.0 with known data."""
        power_freq = calculator.calculate_power_frequency(known_wind_speeds)
        
        # Sum should be 1.0
        total_power_frequency = sum(power_freq.values())
        assert total_power_frequency == pytest.approx(1.0, abs=0.0001)
    
    def test_frequency_values_in_valid_range(
        self, calculator: WindFrequencyCalculator, sample_input_single_height: SingleMastAnalysisInput
    ) -> None:
        """Test that frequency values are in valid range [0, 1]."""
        result = calculator.analyze_by_height(sample_input_single_height)
        
        if len(result.data) > 0:
            for row in result.data.iter_rows(named=True):
                assert 0.0 <= row["frequency"] <= 1.0
                assert 0.0 <= row["power_frequency"] <= 1.0


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_dataframe(self, calculator: WindFrequencyCalculator) -> None:
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
        
        result = calculator.analyze_by_height(input_data)
        
        assert result is not None
        assert len(result.data) == 0
    
    def test_single_row_data(self, calculator: WindFrequencyCalculator) -> None:
        """Test analysis with single row of data."""
        df = pl.DataFrame({
            "timestamp": [datetime(2023, 1, 1)],
            "WS_100m_avg": [5.0],
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
        
        result = calculator.analyze_by_height(input_data)
        
        # Should handle gracefully (less than MIN_SAMPLES)
        assert result is not None
        assert len(result.data) == 0  # Insufficient data
    
    def test_missing_column(self, calculator: WindFrequencyCalculator) -> None:
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
        
        result = calculator.analyze_by_height(input_data)
        
        assert result is not None
        # Should handle gracefully (skip missing column)
        assert len(result.data) == 0
    
    def test_constants(self) -> None:
        """Test that WindFrequencyConstants has expected values."""
        constants = WindFrequencyConstants()
        
        assert constants.BIN_SIZE == 1.0
        assert constants.MAX_BIN == 28.0
        assert constants.HOURS_PER_YEAR == 8760.0
        assert constants.PRODUCTIVE_RANGE == (3.0, 25.0)
        assert constants.MIN_SAMPLES == 10
        assert constants.AIR_DENSITY == 1.225


class TestTimeRangeExtraction:
    """Tests for time range extraction."""

    def test_get_time_range_with_timestamp(self, calculator: WindFrequencyCalculator) -> None:
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
    
    def test_get_time_range_no_timestamp(self, calculator: WindFrequencyCalculator) -> None:
        """Test time range extraction without timestamp column."""
        df = pl.DataFrame({
            "WS_100m_avg": [5.0, 6.0, 7.0],
        })
        
        time_range = calculator._get_time_range(df)
        
        assert time_range == "Unknown"
    
    def test_get_time_range_empty_df(self, calculator: WindFrequencyCalculator) -> None:
        """Test time range extraction from empty DataFrame."""
        df = pl.DataFrame({
            "timestamp": [],
            "WS_100m_avg": [],
        })
        
        time_range = calculator._get_time_range(df)
        
        assert time_range == "Unknown"
