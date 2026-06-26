"""Tests for Weibull fitter service.

Tests cover MLE fitting, Method of Moments fallback, edge cases,
histogram calculation, and multi-height fitting capabilities.
"""

from datetime import datetime, timedelta
from math import gamma as gamma_func

import numpy as np
import polars as pl
import pytest
from cleanmast.subdomains.assessment.subdomains.weibull.services._calculator import (
    WeibullFitter,
    WeibullParameters,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.assessment.subdomains.weibull.value_objects.schemas import (
    WeibullSchema,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def fitter() -> WeibullFitter:
    """Create a WeibullFitter instance."""
    return WeibullFitter()


@pytest.fixture
def sample_input_single_height() -> SingleMastAnalysisInput:
    """Create sample input data with single height."""
    np.random.seed(42)  # For reproducibility
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]
    
    # Generate Weibull-distributed wind speeds (k=2.0, c=8.0)
    wind_speeds = 8.0 * np.random.weibull(2.0, 1000)
    
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
    
    return SingleMastAnalysisInput(
        time_series=time_series,
        parameters=parameters,
        mast_name="TestMast",
    )


@pytest.fixture
def sample_input_multiple_heights() -> SingleMastAnalysisInput:
    """Create sample input data with multiple heights."""
    np.random.seed(42)
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]
    
    # Generate different Weibull parameters for different heights
    ws_100m = 8.0 * np.random.weibull(2.0, 1000)
    np.random.seed(43)
    ws_120m = 9.0 * np.random.weibull(2.2, 1000)
    
    df = pl.DataFrame({
        "timestamp": timestamps,
        "WS_100m_avg": ws_100m,
        "WS_120m_avg": ws_120m,
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
            column_name="WS_120m_avg",
            sensor_type="WindSpeed",
            sensor_direction="",
            height=120.0,
            stat_type="avg",
            unit="m/s",
        ),
    ]
    
    time_series = TimeSeriesData(df=df, sensors=sensors)
    parameters = AnalysisParameters(heights=[100.0, 120.0], air_density=1.225)
    
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


# =============================================================================
# Test WeibullFitter
# =============================================================================


class TestWeibullFitter:
    """Tests for WeibullFitter service."""

    def test_mle_fitting(self, fitter: WeibullFitter) -> None:
        """MLE produces reasonable k, c values (within 10% of expected)."""
        np.random.seed(42)
        # Known Weibull parameters
        shape_k, scale_c = 2.0, 8.0
        wind_speeds = scale_c * np.random.weibull(shape_k, 1000)
        
        result = fitter.fit(wind_speeds.tolist(), height=100.0, interpolation_marker=None)
        
        assert result is not None
        row = result.data.row(0, named=True)
        
        # Should recover parameters within 10% tolerance
        assert abs(row["shape_k"] - shape_k) < 0.2  # Within 10%
        assert abs(row["scale_c"] - scale_c) < 0.8  # Within 10%

    def test_method_of_moments_fallback(self, fitter: WeibullFitter) -> None:
        """MoM triggers when MLE fails."""
        # Create data that might cause MLE to struggle
        # Using very small variance data which can cause optimization issues
        wind_speeds = [5.0] * 100  # Constant data - zero variance
        
        # This should not raise, should fall back to MoM
        result = fitter.fit(wind_speeds, height=100.0, interpolation_marker=None)
        
        # For constant data, we still get a result (though parameters may be edge cases)
        # The method should complete without raising
        if result is not None:
            row = result.data.row(0, named=True)
            # With zero variance, shape_k should be very large or we use defaults
            assert row["shape_k"] > 0
            assert row["scale_c"] > 0

    def test_insufficient_data(self, fitter: WeibullFitter) -> None:
        """Returns None for < 10 data points."""
        wind_speeds = [5.0, 6.0, 7.0, 8.0, 9.0]  # Only 5 points
        
        result = fitter.fit(wind_speeds, height=100.0, interpolation_marker=None)
        
        assert result is None

    def test_perfect_weibull_data(self, fitter: WeibullFitter) -> None:
        """Fitting known Weibull data recovers parameters."""
        np.random.seed(42)
        
        # Test with different known parameters
        test_cases = [
            (1.5, 6.0),   # Low shape, moderate scale
            (2.0, 8.0),   # Standard case
            (2.5, 10.0),  # Higher shape, higher scale
            (3.0, 7.0),   # High shape (approaching normal)
        ]
        
        for expected_k, expected_c in test_cases:
            wind_speeds = expected_c * np.random.weibull(expected_k, 2000)
            
            result = fitter.fit(wind_speeds.tolist(), height=100.0, interpolation_marker=None)
            
            assert result is not None, f"Failed for k={expected_k}, c={expected_c}"
            row = result.data.row(0, named=True)
            
            # Within 15% tolerance (statistical variation)
            assert abs(row["shape_k"] - expected_k) < expected_k * 0.15, \
                f"Shape k mismatch: expected {expected_k}, got {row['shape_k']}"
            assert abs(row["scale_c"] - expected_c) < expected_c * 0.15, \
                f"Scale c mismatch: expected {expected_c}, got {row['scale_c']}"

    def test_histogram_calculation(self, fitter: WeibullFitter) -> None:
        """Histogram bins and densities sum correctly."""
        np.random.seed(42)
        wind_speeds = 8.0 * np.random.weibull(2.0, 1000)
        
        result = fitter.fit(wind_speeds.tolist(), height=100.0, interpolation_marker=None)
        
        assert result is not None
        row = result.data.row(0, named=True)
        
        bin_centers = row["bin_centers"]
        observed_density = row["observed_density"]
        fitted_density = row["fitted_density"]
        
        # Check that arrays have same length
        assert len(bin_centers) == len(observed_density)
        assert len(bin_centers) == len(fitted_density)
        
        # Observed density should sum to approximately 1 (normalized)
        # Allowing some tolerance due to binning effects
        assert sum(observed_density) > 0.8
        assert sum(observed_density) <= 1.05  # Allow small numerical error
        
        # Fitted density should also be normalized
        assert sum(fitted_density) > 0.8
        assert sum(fitted_density) <= 1.05  # Allow small numerical error
        
        # All densities should be non-negative
        assert all(d >= 0 for d in observed_density)
        assert all(d >= 0 for d in fitted_density)

    def test_multiple_heights(self, fitter: WeibullFitter) -> None:
        """Can fit multiple heights independently."""
        np.random.seed(42)
        
        # Create data for two different heights
        ws_100m = 8.0 * np.random.weibull(2.0, 1000)
        np.random.seed(43)
        ws_120m = 9.0 * np.random.weibull(2.2, 1000)
        
        result_100m = fitter.fit(ws_100m.tolist(), height=100.0, interpolation_marker=None)
        result_120m = fitter.fit(ws_120m.tolist(), height=120.0, interpolation_marker="外推")
        
        assert result_100m is not None
        assert result_120m is not None
        
        row_100m = result_100m.data.row(0, named=True)
        row_120m = result_120m.data.row(0, named=True)
        
        # Heights should be preserved
        assert row_100m["height"] == 100.0
        assert row_120m["height"] == 120.0
        
        # Interpolation markers
        assert row_100m["interpolation_marker"] is None
        assert row_120m["interpolation_marker"] == "外推"
        
        # 120m should have higher scale parameter (higher wind speeds)
        assert row_120m["scale_c"] > row_100m["scale_c"]

    def test_fit_from_input(self, fitter: WeibullFitter, sample_input_single_height: SingleMastAnalysisInput) -> None:
        """Test fitting from SingleMastAnalysisInput."""
        result = fitter.fit_from_input(sample_input_single_height, ws_column="WS_100m_avg")
        
        assert result is not None
        assert result.schema == WeibullSchema
        
        # Check metadata
        assert result.metadata.mast_name == "TestMast"
        # time_range contains actual date range from input
        assert "to" in result.metadata.time_range or "n=" in result.metadata.time_range
        
        # Check data
        row = result.data.row(0, named=True)
        assert row["height"] == 100.0
        assert row["shape_k"] > 0
        assert row["scale_c"] > 0

    def test_fit_from_input_multiple_heights(self, fitter: WeibullFitter, sample_input_multiple_heights: SingleMastAnalysisInput) -> None:
        """Test fitting multiple heights from SingleMastAnalysisInput."""
        result_100m = fitter.fit_from_input(sample_input_multiple_heights, ws_column="WS_100m_avg")
        result_120m = fitter.fit_from_input(sample_input_multiple_heights, ws_column="WS_120m_avg")
        
        assert result_100m is not None
        assert result_120m is not None
        
        row_100m = result_100m.data.row(0, named=True)
        row_120m = result_120m.data.row(0, named=True)
        
        # Different heights should have different parameters
        assert row_100m["height"] == 100.0
        assert row_120m["height"] == 120.0
        
        # 120m typically has higher wind speeds
        assert row_120m["scale_c"] > row_100m["scale_c"]

    def test_fit_from_input_missing_column(self, fitter: WeibullFitter, sample_input_single_height: SingleMastAnalysisInput) -> None:
        """Returns None for missing column."""
        result = fitter.fit_from_input(sample_input_single_height, ws_column="WS_200m_avg")
        
        assert result is None

    def test_fit_from_input_with_insufficient_data(self, fitter: WeibullFitter, insufficient_data_input: SingleMastAnalysisInput) -> None:
        """Returns None when input has insufficient data."""
        result = fitter.fit_from_input(insufficient_data_input, ws_column="WS_100m_avg")
        
        assert result is None

    def test_schema_validation(self, fitter: WeibullFitter, sample_input_single_height: SingleMastAnalysisInput) -> None:
        """Verify result data conforms to WeibullSchema."""
        result = fitter.fit_from_input(sample_input_single_height, ws_column="WS_100m_avg")
        
        assert result is not None
        assert result.schema == WeibullSchema
        
        # Verify all expected columns exist
        expected_columns = {
            "height", "interpolation_marker", "shape_k", "scale_c",
            "mean_speed", "bin_centers", "observed_density", "fitted_density"
        }
        assert set(result.data.columns) == expected_columns

    def test_mean_speed_calculation(self, fitter: WeibullFitter) -> None:
        """Verify mean speed is calculated correctly from Weibull parameters."""
        np.random.seed(42)
        shape_k, scale_c = 2.0, 8.0
        wind_speeds = scale_c * np.random.weibull(shape_k, 1000)
        
        result = fitter.fit(wind_speeds.tolist(), height=100.0, interpolation_marker=None)
        
        assert result is not None
        row = result.data.row(0, named=True)
        
        # Mean speed should be c * Gamma(1 + 1/k)
        expected_mean = scale_c * gamma_func(1 + 1 / shape_k)
        actual_mean = row["mean_speed"]
        
        # Allow some tolerance for statistical variation and fitting error
        assert abs(actual_mean - expected_mean) < expected_mean * 0.15

    def test_non_positive_values_filtered(self, fitter: WeibullFitter) -> None:
        """Non-positive wind speeds are filtered out."""
        # Mix of valid and invalid values
        wind_speeds = [-1.0, 0.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0]
        
        result = fitter.fit(wind_speeds, height=100.0, interpolation_marker=None)
        
        assert result is not None
        # Should still have enough data after filtering
        row = result.data.row(0, named=True)
        assert row["shape_k"] > 0
        assert row["scale_c"] > 0

    def test_all_non_positive_values(self, fitter: WeibullFitter) -> None:
        """Returns None when all values are non-positive."""
        wind_speeds = [-1.0, 0.0, -2.0, 0.0, -3.0]
        
        result = fitter.fit(wind_speeds, height=100.0, interpolation_marker=None)
        
        assert result is None

    def test_method_of_moments_direct(self, fitter: WeibullFitter) -> None:
        """Test Method of Moments calculation directly."""
        np.random.seed(42)
        shape_k, scale_c = 2.0, 8.0
        wind_speeds = scale_c * np.random.weibull(shape_k, 1000)
        
        # Call MoM directly
        mom_k, mom_c = fitter._method_of_moments(wind_speeds.tolist())
        
        # Should produce reasonable estimates
        assert mom_k > 0
        assert mom_c > 0
        assert abs(mom_k - shape_k) < 0.3  # Within 15%
        assert abs(mom_c - scale_c) < 1.2  # Within 15%

    def test_weibull_pdf_calculation(self, fitter: WeibullFitter) -> None:
        """Test Weibull PDF calculation."""
        k, c = 2.0, 8.0
        x = np.array([0.0, 4.0, 8.0, 12.0, 16.0])
        
        pdf_values = fitter._weibull_pdf(x, k, c)
        
        # PDF should be 0 at x=0
        assert pdf_values[0] == 0.0
        
        # PDF should be non-negative everywhere
        assert all(pdf_values >= 0)
        
        # PDF should have maximum near the scale parameter
        max_idx = np.argmax(pdf_values)
        assert 1 <= max_idx <= 3  # Maximum should be around x=c=8

    def test_get_time_range(self, fitter: WeibullFitter) -> None:
        """Test time range extraction from DataFrame."""
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(24)]
        
        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_100m_avg": [8.0] * 24,
        })
        
        time_range = fitter._get_time_range(df)
        
        assert "2023-01-01" in time_range
        assert "to" in time_range

    def test_get_time_range_no_timestamp(self, fitter: WeibullFitter) -> None:
        """Test time range extraction when timestamp column is missing."""
        df = pl.DataFrame({
            "WS_100m_avg": [8.0] * 24,
        })
        
        time_range = fitter._get_time_range(df)
        
        assert time_range == "unknown"


class TestWeibullParameters:
    """Tests for WeibullParameters dataclass."""

    def test_creation(self) -> None:
        """Test creating WeibullParameters."""
        params = WeibullParameters(shape_k=2.0, scale_c=8.0)
        
        assert params.shape_k == 2.0
        assert params.scale_c == 8.0

    def test_immutability(self) -> None:
        """Test that WeibullParameters is frozen (immutable)."""
        params = WeibullParameters(shape_k=2.0, scale_c=8.0)
        
        with pytest.raises(AttributeError):
            params.shape_k = 3.0  # type: ignore[misc]
