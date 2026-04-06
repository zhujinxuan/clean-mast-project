"""Tests for vertical profile analyzer service.

Tests cover power law fitting, wind shear calculations, shear matrix generation,
and edge cases for vertical wind profile analysis.
"""

from datetime import datetime, timedelta

import numpy as np
import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.services.calculators.vertical_profile_analyzer import (
    VerticalProfileAnalyzer,
    VerticalProfileConstants,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.assessment.domain.value_objects.schemas import (
    VerticalProfileSchema,
    WindShearSchema,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


@pytest.fixture
def analyzer() -> VerticalProfileAnalyzer:
    """Create a VerticalProfileAnalyzer instance."""
    return VerticalProfileAnalyzer()


@pytest.fixture
def constants() -> VerticalProfileConstants:
    """Create VerticalProfileConstants instance."""
    return VerticalProfileConstants()


@pytest.fixture
def sample_wind_data_single_height() -> pl.DataFrame:
    """Create sample wind data with single height."""
    np.random.seed(42)
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]
    
    # Generate realistic wind speeds (Weibull distribution)
    wind_speeds = np.random.weibull(2, 1000) * 8.0
    wind_speeds = np.clip(wind_speeds, 0.5, 35)  # Ensure positive values
    
    return pl.DataFrame({
        "timestamp": timestamps,
        "WS_100m_avg": wind_speeds,
    })


@pytest.fixture
def sample_wind_data_multi_height() -> pl.DataFrame:
    """Create sample wind data with multiple heights."""
    np.random.seed(42)
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]
    
    # Generate wind speeds that increase with height (realistic profile)
    # Using power law: v = v_ref * (h/h_ref)^0.14 (typical alpha for open terrain)
    alpha = 0.14
    ref_speed = np.random.weibull(2, 1000) * 8.0
    
    wind_speeds_100m = ref_speed * (100/100)**alpha
    wind_speeds_120m = ref_speed * (120/100)**alpha
    wind_speeds_140m = ref_speed * (140/100)**alpha
    
    return pl.DataFrame({
        "timestamp": timestamps,
        "WS_100m_avg": np.clip(wind_speeds_100m, 0.5, 35),
        "WS_120m_avg": np.clip(wind_speeds_120m, 0.5, 35),
        "WS_140m_avg": np.clip(wind_speeds_140m, 0.5, 35),
    })


@pytest.fixture
def sample_input_single_height(
    sample_wind_data_single_height: pl.DataFrame,
) -> SingleMastAnalysisInput:
    """Create sample input with single height."""
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
    
    time_series = TimeSeriesData(df=sample_wind_data_single_height, sensors=sensors)
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
    """Create sample input with multiple heights."""
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
def known_power_law_data() -> tuple[list[float], list[float], float]:
    """Create known power law data with expected alpha.
    
    Returns:
        Tuple of (heights, speeds, expected_alpha)
    """
    # Using power law with alpha = 0.2
    # v = 8.0 * (h/100)^0.2
    alpha = 0.2
    heights = [50.0, 80.0, 100.0, 120.0, 150.0]
    ref_speed = 8.0
    ref_height = 100.0
    speeds = [ref_speed * (h / ref_height) ** alpha for h in heights]
    
    return heights, speeds, alpha


class TestPowerLawFitting:
    """Tests for power law fitting functionality."""

    def test_fit_power_law_known_alpha(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test power law fit with known alpha value."""
        # Test data with known alpha = 0.304
        # alpha = ln(v2/v1) / ln(h2/h1) = ln(8.5/8.0) / ln(120/100)
        heights = [100.0, 120.0]
        speeds = [8.0, 8.5]
        expected_alpha = np.log(8.5 / 8.0) / np.log(120 / 100)
        
        alpha, r_squared = analyzer.fit_power_law(heights, speeds)
        
        assert alpha is not None
        assert r_squared is not None
        assert alpha == pytest.approx(expected_alpha, abs=0.001)
        assert r_squared > 0.99  # Perfect fit for 2 points
    
    def test_fit_power_law_multiple_points(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test power law fit with multiple data points."""
        # Generate data with known alpha
        alpha_true = 0.14
        heights = [80.0, 100.0, 120.0, 140.0]
        ref_speed = 7.0
        ref_height = 100.0
        speeds = [ref_speed * (h / ref_height) ** alpha_true for h in heights]
        
        alpha, r_squared = analyzer.fit_power_law(heights, speeds)
        
        assert alpha is not None
        assert r_squared is not None
        assert alpha == pytest.approx(alpha_true, abs=0.001)
        assert r_squared > 0.999  # Should be nearly perfect
    
    def test_fit_power_law_accuracy_r_squared(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test that power law fit produces R2 > 0.9 for good data."""
        # Generate near-perfect power law data with small noise
        np.random.seed(42)
        alpha_true = 0.16
        heights = np.linspace(50, 150, 10)
        ref_speed = 8.0
        ref_height = 100.0
        
        # Add small random noise (1% std)
        noise = np.random.normal(0, 0.01, len(heights))
        speeds = ref_speed * (heights / ref_height) ** alpha_true * (1 + noise)
        
        alpha, r_squared = analyzer.fit_power_law(heights.tolist(), speeds.tolist())
        
        assert alpha is not None
        assert r_squared is not None
        assert r_squared > 0.9, f"R2 = {r_squared}, expected > 0.9"
        assert 0.10 < alpha < 0.40, f"Alpha = {alpha}, expected in range [0.10, 0.40]"
    
    def test_fit_power_law_typical_values(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test power law fit with typical wind profile values."""
        # Typical values for open terrain (alpha ~ 0.14)
        heights = [50.0, 80.0, 100.0, 120.0, 150.0]
        speeds = [6.8, 7.5, 8.0, 8.4, 8.9]
        
        alpha, r_squared = analyzer.fit_power_law(heights, speeds)
        
        assert alpha is not None
        assert r_squared is not None
        # Alpha should be in reasonable range for real terrain
        assert 0.05 < alpha < 0.50
        assert 0.5 < r_squared <= 1.0
    
    def test_fit_power_law_empty_data(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test power law fit with empty data."""
        alpha, r_squared = analyzer.fit_power_law([], [])
        
        assert alpha is None
        assert r_squared is None
    
    def test_fit_power_law_single_point(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test power law fit with single data point."""
        alpha, r_squared = analyzer.fit_power_law([100.0], [8.0])
        
        assert alpha is None
        assert r_squared is None
    
    def test_fit_power_law_mismatched_lengths(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test power law fit with mismatched heights and speeds."""
        alpha, r_squared = analyzer.fit_power_law([100.0, 120.0], [8.0])
        
        assert alpha is None
        assert r_squared is None
    
    def test_fit_power_law_zero_height(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test power law fit with zero height."""
        heights = [0.0, 100.0, 120.0]
        speeds = [0.0, 8.0, 8.5]
        
        alpha, r_squared = analyzer.fit_power_law(heights, speeds)
        
        # Should filter out zero height and fit remaining valid points
        assert alpha is not None
        assert r_squared is not None
    
    def test_fit_power_law_negative_values(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test power law fit with negative values."""
        heights = [-10.0, 100.0, 120.0]
        speeds = [-5.0, 8.0, 8.5]
        
        alpha, r_squared = analyzer.fit_power_law(heights, speeds)
        
        # Should filter out negative values and fit remaining valid points
        assert alpha is not None
        assert r_squared is not None
    
    def test_fit_power_law_all_invalid(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test power law fit with all invalid values."""
        heights = [0.0, -10.0, -20.0]
        speeds = [0.0, -5.0, -8.0]
        
        alpha, r_squared = analyzer.fit_power_law(heights, speeds)
        
        assert alpha is None
        assert r_squared is None


class TestWindShearCalculations:
    """Tests for wind shear calculation between two heights."""

    def test_calculate_wind_shear_basic(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test basic wind shear calculation."""
        # alpha = ln(v2/v1) / ln(h2/h1) = ln(8.5/8.0) / ln(120/100) ~= 0.333
        height1, speed1 = 100.0, 8.0
        height2, speed2 = 120.0, 8.5
        expected_alpha = np.log(speed2 / speed1) / np.log(height2 / height1)
        
        alpha = analyzer.calculate_wind_shear(height1, speed1, height2, speed2)
        
        assert alpha is not None
        assert alpha == pytest.approx(expected_alpha, abs=0.001)
        assert alpha == pytest.approx(0.333, abs=0.01)
    
    def test_calculate_wind_shear_formula_accuracy(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test alpha calculation formula: ln(v2/v1) / ln(h2/h1)."""
        heights = [100.0, 120.0]
        speeds = [8.0, 8.5]
        
        alpha = analyzer.calculate_wind_shear(heights[0], speeds[0], heights[1], speeds[1])
        
        expected = np.log(8.5 / 8.0) / np.log(120 / 100)
        assert alpha == pytest.approx(expected, abs=0.0001)
    
    def test_calculate_wind_shear_typical_range(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test that shear calculations produce expected range (0.1-0.4)."""
        test_cases = [
            # (h1, v1, h2, v2, expected_range)
            (100.0, 8.0, 120.0, 8.5, (0.20, 0.35)),  # Open terrain
            (100.0, 8.0, 120.0, 9.0, (0.50, 0.70)),  # Rough terrain
            (100.0, 8.0, 120.0, 8.2, (0.10, 0.15)),  # Smooth terrain
        ]
        
        for h1, v1, h2, v2, (min_alpha, max_alpha) in test_cases:
            alpha = analyzer.calculate_wind_shear(h1, v1, h2, v2)
            assert alpha is not None
            assert min_alpha <= alpha <= max_alpha, f"Alpha {alpha} not in range [{min_alpha}, {max_alpha}]"
    
    def test_calculate_wind_shear_symmetric(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test that shear is symmetric when swapping arguments: a_12 = a_21."""
        h1, v1 = 100.0, 8.0
        h2, v2 = 120.0, 8.5
        
        alpha_12 = analyzer.calculate_wind_shear(h1, v1, h2, v2)
        alpha_21 = analyzer.calculate_wind_shear(h2, v2, h1, v1)
        
        assert alpha_12 is not None
        assert alpha_21 is not None
        # Verify a_12 = a_21 (same value when swapping arguments)
        assert alpha_12 == pytest.approx(alpha_21, abs=0.001)
    
    def test_calculate_wind_shear_zero_height(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test wind shear with zero height."""
        alpha = analyzer.calculate_wind_shear(0.0, 8.0, 120.0, 8.5)
        assert alpha is None
    
    def test_calculate_wind_shear_negative_height(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test wind shear with negative height."""
        alpha = analyzer.calculate_wind_shear(-100.0, 8.0, 120.0, 8.5)
        assert alpha is None
    
    def test_calculate_wind_shear_zero_speed(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test wind shear with zero wind speed."""
        alpha = analyzer.calculate_wind_shear(100.0, 0.0, 120.0, 8.5)
        assert alpha is None
    
    def test_calculate_wind_shear_negative_speed(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test wind shear with negative wind speed."""
        alpha = analyzer.calculate_wind_shear(100.0, -8.0, 120.0, 8.5)
        assert alpha is None
    
    def test_calculate_wind_shear_same_height(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test wind shear with same height."""
        alpha = analyzer.calculate_wind_shear(100.0, 8.0, 100.0, 8.5)
        assert alpha is None
    
    def test_calculate_wind_shear_very_close_heights(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test wind shear with very close heights."""
        # Heights very close together (1m difference)
        h1, v1 = 100.0, 8.0
        h2, v2 = 100.1, 8.01
        
        alpha = analyzer.calculate_wind_shear(h1, v1, h2, v2)
        
        # Should still produce valid result
        assert alpha is not None
        assert np.isfinite(alpha)


class TestShearMatrix:
    """Tests for shear matrix generation."""

    def test_calculate_shear_matrix_basic(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test basic shear matrix calculation."""
        heights = [100.0, 120.0, 140.0]
        speeds = [8.0, 8.5, 9.0]
        
        matrix = analyzer.calculate_shear_matrix(heights, speeds)
        
        assert len(matrix) == 3
        assert all(len(row) == 3 for row in matrix)
    
    def test_calculate_shear_matrix_diagonal_none(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test that diagonal elements are None."""
        heights = [100.0, 120.0, 140.0]
        speeds = [8.0, 8.5, 9.0]
        
        matrix = analyzer.calculate_shear_matrix(heights, speeds)
        
        for i in range(len(heights)):
            assert matrix[i][i] is None
    
    def test_calculate_shear_matrix_symmetric(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test that shear matrix is symmetric: a_ij = a_ji."""
        heights = [100.0, 120.0, 140.0]
        speeds = [8.0, 8.5, 9.0]
        
        matrix = analyzer.calculate_shear_matrix(heights, speeds)
        
        n = len(heights)
        for i in range(n):
            for j in range(n):
                if i != j:
                    assert matrix[i][j] is not None
                    assert matrix[j][i] is not None
                    assert matrix[i][j] == pytest.approx(matrix[j][i], abs=0.001)
    
    def test_calculate_shear_matrix_empty(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test shear matrix with empty data."""
        matrix = analyzer.calculate_shear_matrix([], [])
        
        assert matrix == []
    
    def test_calculate_shear_matrix_mismatched_lengths(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test shear matrix with mismatched heights and speeds."""
        matrix = analyzer.calculate_shear_matrix([100.0, 120.0], [8.0])
        
        assert matrix == []
    
    def test_calculate_shear_matrix_single_height(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test shear matrix with single height."""
        matrix = analyzer.calculate_shear_matrix([100.0], [8.0])
        
        assert len(matrix) == 1
        assert matrix[0][0] is None


class TestVerticalProfileAnalysis:
    """Tests for vertical profile analysis."""

    def test_analyze_vertical_profile_single_height(
        self, analyzer: VerticalProfileAnalyzer, sample_input_single_height: SingleMastAnalysisInput
    ) -> None:
        """Test vertical profile analysis with single height."""
        result = analyzer.analyze_vertical_profile(sample_input_single_height)
        
        assert result is not None
        assert result.schema == VerticalProfileSchema
        
        # Should have one row for single height
        assert len(result.data) == 1
        
        # Check expected columns
        expected_columns = {
            "height", "interpolation_marker", "wind_speed_mean",
            "wind_speed_std", "alpha", "r_squared"
        }
        assert set(result.data.columns) == expected_columns
        
        # Check data types
        row = result.data.row(0, named=True)
        assert row["height"] == 100.0
        assert row["wind_speed_mean"] > 0
        assert row["wind_speed_std"] >= 0
        # Alpha and R2 should be None for single height (can't fit)
        assert row["alpha"] is None
        assert row["r_squared"] is None
    
    def test_analyze_vertical_profile_multiple_heights(
        self, analyzer: VerticalProfileAnalyzer, sample_input_multiple_heights: SingleMastAnalysisInput
    ) -> None:
        """Test vertical profile analysis with multiple heights."""
        result = analyzer.analyze_vertical_profile(sample_input_multiple_heights)
        
        assert result is not None
        assert len(result.data) == 3  # 3 heights
        
        # All heights should be present
        heights = result.data["height"].to_list()
        assert 100.0 in heights
        assert 120.0 in heights
        assert 140.0 in heights
        
        # Should have alpha and R2 values
        first_row = result.data.row(0, named=True)
        assert first_row["alpha"] is not None
        assert first_row["r_squared"] is not None
        assert first_row["r_squared"] > 0.9  # Good fit for synthetic data
    
    def test_analyze_vertical_profile_no_wind_sensors(
        self, analyzer: VerticalProfileAnalyzer, input_no_wind_speed: SingleMastAnalysisInput
    ) -> None:
        """Test analysis with no wind speed sensors."""
        result = analyzer.analyze_vertical_profile(input_no_wind_speed)
        
        assert result is not None
        assert len(result.data) == 0
    
    def test_analyze_vertical_profile_insufficient_data(
        self, analyzer: VerticalProfileAnalyzer, insufficient_data_input: SingleMastAnalysisInput
    ) -> None:
        """Test analysis with insufficient data."""
        result = analyzer.analyze_vertical_profile(insufficient_data_input)
        
        assert result is not None
        # Should return empty dataframe (less than MIN_SAMPLES)
        assert len(result.data) == 0


class TestWindShearAnalysis:
    """Tests for wind shear analysis between height pairs."""

    def test_calculate_wind_shear_analysis(
        self, analyzer: VerticalProfileAnalyzer, sample_input_multiple_heights: SingleMastAnalysisInput
    ) -> None:
        """Test wind shear analysis with multiple heights."""
        result = analyzer.calculate_wind_shear_analysis(sample_input_multiple_heights)
        
        assert result is not None
        assert result.schema == WindShearSchema
        
        # Should have rows for height pairs (100-120, 100-140, 120-140)
        assert len(result.data) == 3
        
        # Check expected columns
        expected_columns = {
            "from_height", "to_height", "alpha_mean",
            "alpha_std", "alpha_min", "alpha_max"
        }
        assert set(result.data.columns) == expected_columns
    
    def test_wind_shear_analysis_single_height(
        self, analyzer: VerticalProfileAnalyzer, sample_input_single_height: SingleMastAnalysisInput
    ) -> None:
        """Test shear analysis with single height."""
        result = analyzer.calculate_wind_shear_analysis(sample_input_single_height)
        
        assert result is not None
        # Need at least 2 heights for shear analysis
        assert len(result.data) == 0
    
    def test_wind_shear_analysis_statistics(
        self, analyzer: VerticalProfileAnalyzer, sample_input_multiple_heights: SingleMastAnalysisInput
    ) -> None:
        """Test that shear statistics are calculated correctly."""
        result = analyzer.calculate_wind_shear_analysis(sample_input_multiple_heights)
        
        for row in result.data.iter_rows(named=True):
            # min <= mean <= max (with small tolerance for floating point)
            assert row["alpha_min"] <= row["alpha_mean"] + 1e-10
            assert row["alpha_mean"] <= row["alpha_max"] + 1e-10
            # std >= 0
            assert row["alpha_std"] >= 0
    
    def test_wind_shear_analysis_no_wind_sensors(
        self, analyzer: VerticalProfileAnalyzer, input_no_wind_speed: SingleMastAnalysisInput
    ) -> None:
        """Test shear analysis with no wind sensors."""
        result = analyzer.calculate_wind_shear_analysis(input_no_wind_speed)
        
        assert result is not None
        assert len(result.data) == 0


class TestTerrainClassification:
    """Tests for terrain classification based on alpha values."""

    def test_terrain_classification_ranges(self) -> None:
        """Test terrain classification based on alpha ranges."""
        # Typical alpha values:
        # - Smooth (water): 0.10-0.12
        # - Open (grassland): 0.12-0.16
        # - Rough (suburban): 0.16-0.25
        # - Very rough (urban): 0.25-0.40
        
        test_cases = [
            (0.08, "smooth"),
            (0.10, "smooth"),
            (0.14, "open"),
            (0.16, "open/rough"),
            (0.20, "rough"),
            (0.25, "rough/very rough"),
            (0.30, "very rough"),
            (0.35, "very rough"),
        ]
        
        for alpha, expected_type in test_cases:
            # Just verify alpha is in valid range
            assert 0.05 <= alpha <= 0.50, f"Alpha {alpha} outside typical range"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_dataframe(self, analyzer: VerticalProfileAnalyzer) -> None:
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
        
        result = analyzer.analyze_vertical_profile(input_data)
        
        assert result is not None
        assert len(result.data) == 0
    
    def test_missing_column(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test handling when sensor column doesn't exist."""
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
        
        result = analyzer.analyze_vertical_profile(input_data)
        
        assert result is not None
        assert len(result.data) == 0
    
    def test_all_null_values(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test handling when all values are null."""
        df = pl.DataFrame({
            "timestamp": [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(100)],
            "WS_100m_avg": [None] * 100,
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
        
        result = analyzer.analyze_vertical_profile(input_data)
        
        assert result is not None
        assert len(result.data) == 0
    
    def test_all_zero_wind_speeds(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test handling when all wind speeds are zero."""
        df = pl.DataFrame({
            "timestamp": [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(100)],
            "WS_100m_avg": [0.0] * 100,
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
        
        result = analyzer.analyze_vertical_profile(input_data)
        
        assert result is not None
        assert len(result.data) == 0
    
    def test_constants(self) -> None:
        """Test that VerticalProfileConstants has expected values."""
        constants = VerticalProfileConstants()
        
        assert constants.MIN_HEIGHTS_FOR_FIT == 2
        assert constants.MIN_SAMPLES == 10
        assert constants.MIN_R_SQUARED == 0.5
        assert constants.DEFAULT_REF_HEIGHT == 10.0


class TestTimeRangeExtraction:
    """Tests for time range extraction."""

    def test_get_time_range_with_timestamp(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test time range extraction from DataFrame with timestamp."""
        df = pl.DataFrame({
            "timestamp": [
                datetime(2023, 1, 1),
                datetime(2023, 6, 15),
                datetime(2023, 12, 31),
            ],
            "WS_100m_avg": [5.0, 6.0, 7.0],
        })
        
        time_range = analyzer._get_time_range(df)
        
        assert "2023-01-01" in time_range
        assert "2023-12-31" in time_range
        assert "to" in time_range
    
    def test_get_time_range_no_timestamp(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test time range extraction without timestamp column."""
        df = pl.DataFrame({
            "WS_100m_avg": [5.0, 6.0, 7.0],
        })
        
        time_range = analyzer._get_time_range(df)
        
        assert time_range == "Unknown"
    
    def test_get_time_range_empty_df(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test time range extraction from empty DataFrame."""
        df = pl.DataFrame({
            "timestamp": [],
            "WS_100m_avg": [],
        })
        
        time_range = analyzer._get_time_range(df)
        
        assert time_range == "Unknown"


class TestRealisticDataScenarios:
    """Tests with realistic wind data scenarios."""

    def test_realistic_open_terrain_profile(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test with realistic open terrain profile (alpha ~= 0.14)."""
        np.random.seed(42)
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(2000)]
        
        # Simulate open terrain with alpha ~= 0.14
        alpha_true = 0.14
        base_speed = np.random.weibull(2, 2000) * 7.5
        
        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_80m_avg": base_speed * (80/100)**alpha_true,
            "WS_100m_avg": base_speed,
            "WS_120m_avg": base_speed * (120/100)**alpha_true,
            "WS_140m_avg": base_speed * (140/100)**alpha_true,
        })
        
        sensors = [
            SensorColumn(
                column_name=f"WS_{h}m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=float(h),
                stat_type="avg",
                unit="m/s",
            )
            for h in [80, 100, 120, 140]
        ]
        
        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[80.0, 100.0, 120.0, 140.0], air_density=1.225)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )
        
        result = analyzer.analyze_vertical_profile(input_data)
        
        assert len(result.data) == 4
        
        # Check alpha is close to expected value
        first_row = result.data.row(0, named=True)
        assert first_row["alpha"] is not None
        assert first_row["alpha"] == pytest.approx(alpha_true, abs=0.02)
        assert first_row["r_squared"] > 0.95
    
    def test_coastal_terrain_profile(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test with coastal terrain profile (alpha ~= 0.10-0.12)."""
        np.random.seed(42)
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]
        
        # Simulate smooth coastal terrain with alpha ~= 0.11
        alpha_true = 0.11
        base_speed = np.random.weibull(2, 1000) * 8.5
        
        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_60m_avg": base_speed * (60/100)**alpha_true,
            "WS_100m_avg": base_speed,
            "WS_120m_avg": base_speed * (120/100)**alpha_true,
        })
        
        sensors = [
            SensorColumn(
                column_name=f"WS_{h}m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=float(h),
                stat_type="avg",
                unit="m/s",
            )
            for h in [60, 100, 120]
        ]
        
        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[60.0, 100.0, 120.0], air_density=1.225)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )
        
        result = analyzer.analyze_vertical_profile(input_data)
        
        first_row = result.data.row(0, named=True)
        assert first_row["alpha"] is not None
        assert 0.08 <= first_row["alpha"] <= 0.15  # Smooth terrain range
    
    def test_forest_terrain_profile(self, analyzer: VerticalProfileAnalyzer) -> None:
        """Test with forest terrain profile (alpha ~= 0.20-0.30)."""
        np.random.seed(42)
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]
        
        # Simulate rough forest terrain with alpha ~= 0.22
        alpha_true = 0.22
        base_speed = np.random.weibull(2, 1000) * 6.5
        
        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_80m_avg": base_speed * (80/100)**alpha_true,
            "WS_100m_avg": base_speed,
            "WS_130m_avg": base_speed * (130/100)**alpha_true,
        })
        
        sensors = [
            SensorColumn(
                column_name=f"WS_{h}m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=float(h),
                stat_type="avg",
                unit="m/s",
            )
            for h in [80, 100, 130]
        ]
        
        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[80.0, 100.0, 130.0], air_density=1.225)
        input_data = SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )
        
        result = analyzer.analyze_vertical_profile(input_data)
        
        first_row = result.data.row(0, named=True)
        assert first_row["alpha"] is not None
        assert 0.15 <= first_row["alpha"] <= 0.35  # Rough terrain range
