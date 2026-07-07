"""Tests for vertical profile analyzer — reporting domain.

Ported from tests/assessment/vertical_profile/test_vertical_profile_analyzer.py.
Test logic preserved; only import paths updated.
"""

from datetime import datetime, timedelta

import numpy as np
import polars as pl
import pytest
from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
from cleanmast.subdomains.reporting.model.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.reporting.model.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.reporting.subdomains.vertical_profile.compute import (
    VerticalProfileAnalyzer,
    VerticalProfileConstants,
)
from cleanmast.subdomains.reporting.subdomains.vertical_profile.model.schemas import (
    VerticalProfileSchema,
    WindShearAggregateProfileSchema,
)


@pytest.fixture
def analyzer() -> VerticalProfileAnalyzer:
    return VerticalProfileAnalyzer()


@pytest.fixture
def constants() -> VerticalProfileConstants:
    return VerticalProfileConstants()


@pytest.fixture
def sample_wind_data_single_height() -> pl.DataFrame:
    np.random.seed(42)
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]
    wind_speeds = np.random.weibull(2, 1000) * 8.0
    wind_speeds = np.clip(wind_speeds, 0.5, 35)
    return pl.DataFrame({
        "timestamp": timestamps,
        "WS_100m_avg": wind_speeds,
    })


@pytest.fixture
def sample_wind_data_multi_height() -> pl.DataFrame:
    np.random.seed(42)
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]
    alpha = 0.14
    ref_speed = np.random.weibull(2, 1000) * 8.0
    wind_speeds_100m = ref_speed * (100 / 100)**alpha
    wind_speeds_120m = ref_speed * (120 / 100)**alpha
    wind_speeds_140m = ref_speed * (140 / 100)**alpha
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
    alpha = 0.2
    heights = [50.0, 80.0, 100.0, 120.0, 150.0]
    ref_speed = 8.0
    ref_height = 100.0
    speeds = [ref_speed * (h / ref_height) ** alpha for h in heights]
    return heights, speeds, alpha


class TestPowerLawFitting:
    def test_fit_power_law_known_alpha(self, analyzer: VerticalProfileAnalyzer) -> None:
        heights = [100.0, 120.0]
        speeds = [8.0, 8.5]
        expected_alpha = np.log(8.5 / 8.0) / np.log(120 / 100)
        alpha, r_squared = analyzer.fit_power_law(heights, speeds)
        assert alpha is not None
        assert r_squared is not None
        assert alpha == pytest.approx(expected_alpha, abs=0.001)
        assert r_squared > 0.99

    def test_fit_power_law_multiple_points(self, analyzer: VerticalProfileAnalyzer) -> None:
        alpha_true = 0.14
        heights = [80.0, 100.0, 120.0, 140.0]
        ref_speed = 7.0
        ref_height = 100.0
        speeds = [ref_speed * (h / ref_height) ** alpha_true for h in heights]
        alpha, r_squared = analyzer.fit_power_law(heights, speeds)
        assert alpha is not None
        assert r_squared is not None
        assert alpha == pytest.approx(alpha_true, abs=0.001)
        assert r_squared > 0.999

    def test_fit_power_law_accuracy_r_squared(self, analyzer: VerticalProfileAnalyzer) -> None:
        np.random.seed(42)
        alpha_true = 0.16
        heights = np.linspace(50, 150, 10)
        ref_speed = 8.0
        ref_height = 100.0
        noise = np.random.normal(0, 0.01, len(heights))
        speeds = ref_speed * (heights / ref_height) ** alpha_true * (1 + noise)
        alpha, r_squared = analyzer.fit_power_law(heights.tolist(), speeds.tolist())
        assert alpha is not None
        assert r_squared is not None
        assert r_squared > 0.9, f"R2 = {r_squared}, expected > 0.9"
        assert 0.10 < alpha < 0.40, f"Alpha = {alpha}, expected in range [0.10, 0.40]"

    def test_fit_power_law_typical_values(self, analyzer: VerticalProfileAnalyzer) -> None:
        heights = [50.0, 80.0, 100.0, 120.0, 150.0]
        speeds = [6.8, 7.5, 8.0, 8.4, 8.9]
        alpha, r_squared = analyzer.fit_power_law(heights, speeds)
        assert alpha is not None
        assert r_squared is not None
        assert 0.05 < alpha < 0.50
        assert 0.5 < r_squared <= 1.0

    def test_fit_power_law_empty_data(self, analyzer: VerticalProfileAnalyzer) -> None:
        alpha, r_squared = analyzer.fit_power_law([], [])
        assert alpha is None
        assert r_squared is None

    def test_fit_power_law_single_point(self, analyzer: VerticalProfileAnalyzer) -> None:
        alpha, r_squared = analyzer.fit_power_law([100.0], [8.0])
        assert alpha is None
        assert r_squared is None

    def test_fit_power_law_mismatched_lengths(self, analyzer: VerticalProfileAnalyzer) -> None:
        alpha, r_squared = analyzer.fit_power_law([100.0, 120.0], [8.0])
        assert alpha is None
        assert r_squared is None

    def test_fit_power_law_zero_height(self, analyzer: VerticalProfileAnalyzer) -> None:
        heights = [0.0, 100.0, 120.0]
        speeds = [0.0, 8.0, 8.5]
        alpha, r_squared = analyzer.fit_power_law(heights, speeds)
        assert alpha is not None
        assert r_squared is not None

    def test_fit_power_law_negative_values(self, analyzer: VerticalProfileAnalyzer) -> None:
        heights = [-10.0, 100.0, 120.0]
        speeds = [-5.0, 8.0, 8.5]
        alpha, r_squared = analyzer.fit_power_law(heights, speeds)
        assert alpha is not None
        assert r_squared is not None

    def test_fit_power_law_all_invalid(self, analyzer: VerticalProfileAnalyzer) -> None:
        heights = [0.0, -10.0, -20.0]
        speeds = [0.0, -5.0, -8.0]
        alpha, r_squared = analyzer.fit_power_law(heights, speeds)
        assert alpha is None
        assert r_squared is None


class TestWindShearCalculations:
    def test_calculate_wind_shear_basic(self, analyzer: VerticalProfileAnalyzer) -> None:
        height1, speed1 = 100.0, 8.0
        height2, speed2 = 120.0, 8.5
        expected_alpha = np.log(speed2 / speed1) / np.log(height2 / height1)
        alpha = analyzer.calculate_wind_shear(height1, speed1, height2, speed2)
        assert alpha is not None
        assert alpha == pytest.approx(expected_alpha, abs=0.001)
        assert alpha == pytest.approx(0.333, abs=0.01)

    def test_calculate_wind_shear_formula_accuracy(self, analyzer: VerticalProfileAnalyzer) -> None:
        heights = [100.0, 120.0]
        speeds = [8.0, 8.5]
        alpha = analyzer.calculate_wind_shear(heights[0], speeds[0], heights[1], speeds[1])
        expected = np.log(8.5 / 8.0) / np.log(120 / 100)
        assert alpha == pytest.approx(expected, abs=0.0001)

    def test_calculate_wind_shear_typical_range(self, analyzer: VerticalProfileAnalyzer) -> None:
        test_cases = [
            (100.0, 8.0, 120.0, 8.5, (0.20, 0.35)),
            (100.0, 8.0, 120.0, 9.0, (0.50, 0.70)),
            (100.0, 8.0, 120.0, 8.2, (0.10, 0.15)),
        ]
        for h1, v1, h2, v2, (min_alpha, max_alpha) in test_cases:
            alpha = analyzer.calculate_wind_shear(h1, v1, h2, v2)
            assert alpha is not None
            assert min_alpha <= alpha <= max_alpha, f"Alpha {alpha} not in range [{min_alpha}, {max_alpha}]"

    def test_calculate_wind_shear_symmetric(self, analyzer: VerticalProfileAnalyzer) -> None:
        h1, v1 = 100.0, 8.0
        h2, v2 = 120.0, 8.5
        alpha_12 = analyzer.calculate_wind_shear(h1, v1, h2, v2)
        alpha_21 = analyzer.calculate_wind_shear(h2, v2, h1, v1)
        assert alpha_12 is not None
        assert alpha_21 is not None
        assert alpha_12 == pytest.approx(alpha_21, abs=0.001)

    def test_calculate_wind_shear_zero_height(self, analyzer: VerticalProfileAnalyzer) -> None:
        alpha = analyzer.calculate_wind_shear(0.0, 8.0, 120.0, 8.5)
        assert alpha is None

    def test_calculate_wind_shear_negative_height(self, analyzer: VerticalProfileAnalyzer) -> None:
        alpha = analyzer.calculate_wind_shear(-100.0, 8.0, 120.0, 8.5)
        assert alpha is None

    def test_calculate_wind_shear_zero_speed(self, analyzer: VerticalProfileAnalyzer) -> None:
        alpha = analyzer.calculate_wind_shear(100.0, 0.0, 120.0, 8.5)
        assert alpha is None

    def test_calculate_wind_shear_negative_speed(self, analyzer: VerticalProfileAnalyzer) -> None:
        alpha = analyzer.calculate_wind_shear(100.0, -8.0, 120.0, 8.5)
        assert alpha is None

    def test_calculate_wind_shear_same_height(self, analyzer: VerticalProfileAnalyzer) -> None:
        alpha = analyzer.calculate_wind_shear(100.0, 8.0, 100.0, 8.5)
        assert alpha is None

    def test_calculate_wind_shear_very_close_heights(self, analyzer: VerticalProfileAnalyzer) -> None:
        h1, v1 = 100.0, 8.0
        h2, v2 = 100.1, 8.01
        alpha = analyzer.calculate_wind_shear(h1, v1, h2, v2)
        assert alpha is not None
        assert np.isfinite(alpha)


class TestVerticalProfileAnalysis:
    def test_analyze_vertical_profile_single_height(
        self, analyzer: VerticalProfileAnalyzer, sample_input_single_height: SingleMastAnalysisInput
    ) -> None:
        result = analyzer.analyze_vertical_profile(sample_input_single_height)
        assert result is not None
        assert result.schema == VerticalProfileSchema
        assert len(result.data) == 1
        expected_columns = {
            "height", "interpolation_marker", "wind_speed_mean",
            "wind_speed_std", "alpha", "r_squared"
        }
        assert set(result.data.columns) == expected_columns
        row = result.data.row(0, named=True)
        assert row["height"] == 100.0
        assert row["wind_speed_mean"] > 0
        assert row["wind_speed_std"] >= 0
        assert row["alpha"] is None
        assert row["r_squared"] is None

    def test_analyze_vertical_profile_multiple_heights(
        self, analyzer: VerticalProfileAnalyzer, sample_input_multiple_heights: SingleMastAnalysisInput
    ) -> None:
        result = analyzer.analyze_vertical_profile(sample_input_multiple_heights)
        assert result is not None
        assert len(result.data) == 3
        heights = result.data["height"].to_list()
        assert 100.0 in heights
        assert 120.0 in heights
        assert 140.0 in heights
        first_row = result.data.row(0, named=True)
        assert first_row["alpha"] is not None
        assert first_row["r_squared"] is not None
        assert first_row["r_squared"] > 0.9

    def test_analyze_vertical_profile_no_wind_sensors(
        self, analyzer: VerticalProfileAnalyzer, input_no_wind_speed: SingleMastAnalysisInput
    ) -> None:
        result = analyzer.analyze_vertical_profile(input_no_wind_speed)
        assert result is not None
        assert len(result.data) == 0

    def test_analyze_vertical_profile_insufficient_data(
        self, analyzer: VerticalProfileAnalyzer, insufficient_data_input: SingleMastAnalysisInput
    ) -> None:
        result = analyzer.analyze_vertical_profile(insufficient_data_input)
        assert result is not None
        assert len(result.data) == 0


class TestWindShearProfile:
    def test_calculate_wind_shear_profile(
        self, analyzer: VerticalProfileAnalyzer, sample_input_multiple_heights: SingleMastAnalysisInput
    ) -> None:
        result = analyzer.calculate_wind_shear_profile(sample_input_multiple_heights)
        assert result is not None
        assert result.schema == WindShearAggregateProfileSchema
        assert len(result.data) == 3
        expected_columns = {"from_height", "to_height", "from_v", "to_v", "alpha"}
        assert set(result.data.columns) == expected_columns

    def test_wind_shear_profile_single_height(
        self, analyzer: VerticalProfileAnalyzer, sample_input_single_height: SingleMastAnalysisInput
    ) -> None:
        result = analyzer.calculate_wind_shear_profile(sample_input_single_height)
        assert result is not None
        assert len(result.data) == 0

    def test_wind_shear_profile_no_wind_sensors(
        self, analyzer: VerticalProfileAnalyzer, input_no_wind_speed: SingleMastAnalysisInput
    ) -> None:
        result = analyzer.calculate_wind_shear_profile(input_no_wind_speed)
        assert result is not None
        assert len(result.data) == 0


class TestTerrainClassification:
    def test_terrain_classification_ranges(self) -> None:
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
            assert 0.05 <= alpha <= 0.50, f"Alpha {alpha} outside typical range"


class TestEdgeCases:
    def test_empty_dataframe(self, analyzer: VerticalProfileAnalyzer) -> None:
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
        constants = VerticalProfileConstants()
        assert constants.MIN_HEIGHTS_FOR_FIT == 2
        assert constants.MIN_SAMPLES == 10
        assert constants.MIN_R_SQUARED == 0.5
        assert constants.DEFAULT_REF_HEIGHT == 10.0


class TestTimeRangeExtraction:
    def test_get_time_range_with_timestamp(self, analyzer: VerticalProfileAnalyzer) -> None:
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
        df = pl.DataFrame({
            "WS_100m_avg": [5.0, 6.0, 7.0],
        })
        time_range = analyzer._get_time_range(df)
        assert time_range == "Unknown"

    def test_get_time_range_empty_df(self, analyzer: VerticalProfileAnalyzer) -> None:
        df = pl.DataFrame({
            "timestamp": [],
            "WS_100m_avg": [],
        })
        time_range = analyzer._get_time_range(df)
        assert time_range == "Unknown"


class TestRealisticDataScenarios:
    def test_realistic_open_terrain_profile(self, analyzer: VerticalProfileAnalyzer) -> None:
        np.random.seed(42)
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(2000)]
        alpha_true = 0.14
        base_speed = np.random.weibull(2, 2000) * 7.5
        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_80m_avg": base_speed * (80 / 100)**alpha_true,
            "WS_100m_avg": base_speed,
            "WS_120m_avg": base_speed * (120 / 100)**alpha_true,
            "WS_140m_avg": base_speed * (140 / 100)**alpha_true,
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
        first_row = result.data.row(0, named=True)
        assert first_row["alpha"] is not None
        assert first_row["alpha"] == pytest.approx(alpha_true, abs=0.02)
        assert first_row["r_squared"] > 0.95

    def test_coastal_terrain_profile(self, analyzer: VerticalProfileAnalyzer) -> None:
        np.random.seed(42)
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]
        alpha_true = 0.11
        base_speed = np.random.weibull(2, 1000) * 8.5
        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_60m_avg": base_speed * (60 / 100)**alpha_true,
            "WS_100m_avg": base_speed,
            "WS_120m_avg": base_speed * (120 / 100)**alpha_true,
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
        assert 0.08 <= first_row["alpha"] <= 0.15

    def test_forest_terrain_profile(self, analyzer: VerticalProfileAnalyzer) -> None:
        np.random.seed(42)
        timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(1000)]
        alpha_true = 0.22
        base_speed = np.random.weibull(2, 1000) * 6.5
        df = pl.DataFrame({
            "timestamp": timestamps,
            "WS_80m_avg": base_speed * (80 / 100)**alpha_true,
            "WS_100m_avg": base_speed,
            "WS_130m_avg": base_speed * (130 / 100)**alpha_true,
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
        assert 0.15 <= first_row["alpha"] <= 0.35
