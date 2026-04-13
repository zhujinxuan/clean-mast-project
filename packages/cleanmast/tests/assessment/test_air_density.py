"""Tests for air density calculation module.

Task 16 of Wave 3: Migrated from tests/report/test_meta.py
Tests updated for analysis.value_objects.air_density API.
"""

import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.value_objects.air_density import (
    GAS_CONSTANT_DRY_AIR,
    HPA_TO_PA,
    KELVIN_OFFSET,
    STANDARD_AIR_DENSITY,
    _normalize_pressure,
    _normalize_temperature,
    calculate_air_density,
    calculate_air_density_for_height,
    convert_to_standard_air_density,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


class TestConstants:
    """Tests for module constants."""

    def test_gas_constant_value(self) -> None:
        """Test gas constant has correct value."""
        assert GAS_CONSTANT_DRY_AIR == 287.05

    def test_standard_air_density_value(self) -> None:
        """Test standard air density has correct value."""
        assert STANDARD_AIR_DENSITY == 1.225

    def test_kelvin_offset_value(self) -> None:
        """Test Kelvin offset has correct value."""
        assert KELVIN_OFFSET == 273.15

    def test_hpa_to_pa_conversion(self) -> None:
        """Test hPa to Pa conversion factor."""
        assert HPA_TO_PA == 100


class TestNormalizeTemperature:
    """Tests for _normalize_temperature helper."""

    def test_celsius_to_kelvin(self) -> None:
        """Test conversion from Celsius to Kelvin."""
        result = _normalize_temperature(15.0)
        assert result == 288.15  # 15 + 273.15

    def test_already_kelvin(self) -> None:
        """Test that Kelvin values are returned unchanged."""
        result = _normalize_temperature(300.0)
        assert result == 300.0

    def test_boundary_at_100(self) -> None:
        """Test boundary condition at 100 degrees."""
        # 100 should be treated as Kelvin (below 100 is Celsius)
        result = _normalize_temperature(100.0)
        assert result == 100.0


class TestNormalizePressure:
    """Tests for _normalize_pressure helper."""

    def test_hpa_to_pa(self) -> None:
        """Test conversion from hPa to Pa."""
        result = _normalize_pressure(1013.25)
        assert result == 101325.0  # 1013.25 * 100

    def test_already_pa(self) -> None:
        """Test that Pa values are returned unchanged."""
        result = _normalize_pressure(101325.0)
        assert result == 101325.0

    def test_boundary_at_10000(self) -> None:
        """Test boundary condition at 10000 Pa."""
        result = _normalize_pressure(10000.0)
        assert result == 10000.0


class TestCalculateAirDensity:
    """Tests for calculate_air_density function."""

    def _create_test_data(
        self,
        temp_values: list[float | None],
        pressure_values: list[float | None],
        temp_height: float = 10.0,
        pressure_height: float = 10.0,
    ) -> TimeSeriesData:
        """Helper to create TimeSeriesData with sensors."""
        df = pl.DataFrame({
            "temperature_avg": temp_values,
            "pressure_avg": pressure_values,
        })

        sensors = [
            SensorColumn(
                column_name="temperature_avg",
                sensor_type="Temperature",
                sensor_direction="",
                height=temp_height,
                stat_type="avg",
                unit="C",
            ),
            SensorColumn(
                column_name="pressure_avg",
                sensor_type="Pressure",
                sensor_direction="",
                height=pressure_height,
                stat_type="avg",
                unit="hPa",
            ),
        ]

        return TimeSeriesData(df=df, sensors=sensors)

    def test_with_valid_data(self) -> None:
        """Test calculation with valid temperature and pressure."""
        data = self._create_test_data(
            temp_values=[15.0, 16.0, 14.0],  # Celsius
            pressure_values=[1013.25, 1014.0, 1012.0],  # hPa
        )

        result = calculate_air_density(data)

        # Expected: ρ = P / (R * T)
        # T_avg = 15°C = 288.15 K
        # P_avg = 1013.083... hPa = 101308.3 Pa
        # ρ = 101308.3 / (287.05 * 288.15) ≈ 1.225
        assert pytest.approx(result, rel=0.01) == 1.225

    def test_missing_temperature_sensor_returns_standard(self) -> None:
        """Test that missing temperature sensor returns standard air density."""
        df = pl.DataFrame({
            "pressure_avg": [1013.25],
        })
        sensors = [
            SensorColumn(
                column_name="pressure_avg",
                sensor_type="Pressure",
                sensor_direction="",
                height=10.0,
                stat_type="avg",
                unit="hPa",
            ),
        ]
        data = TimeSeriesData(df=df, sensors=sensors)

        result = calculate_air_density(data)

        assert result == STANDARD_AIR_DENSITY

    def test_missing_pressure_sensor_returns_standard(self) -> None:
        """Test that missing pressure sensor returns standard air density."""
        df = pl.DataFrame({
            "temperature_avg": [15.0],
        })
        sensors = [
            SensorColumn(
                column_name="temperature_avg",
                sensor_type="Temperature",
                sensor_direction="",
                height=10.0,
                stat_type="avg",
                unit="C",
            ),
        ]
        data = TimeSeriesData(df=df, sensors=sensors)

        result = calculate_air_density(data)

        assert result == STANDARD_AIR_DENSITY

    def test_no_sensors_returns_standard(self) -> None:
        """Test that no sensors returns standard air density."""
        df = pl.DataFrame({
            "ws_avg": [5.0],
        })
        data = TimeSeriesData(df=df, sensors=[])

        result = calculate_air_density(data)

        assert result == STANDARD_AIR_DENSITY

    def test_none_values_returns_standard(self) -> None:
        """Test that None mean values return standard air density."""
        data = self._create_test_data(
            temp_values=[None, None],
            pressure_values=[None, None],
        )

        result = calculate_air_density(data)

        assert result == STANDARD_AIR_DENSITY

    def test_empty_dataframe_returns_standard(self) -> None:
        """Test that empty DataFrame returns standard air density."""
        df = pl.DataFrame({
            "temperature_avg": [],
            "pressure_avg": [],
        })
        sensors = [
            SensorColumn(
                column_name="temperature_avg",
                sensor_type="Temperature",
                sensor_direction="",
                height=10.0,
                stat_type="avg",
                unit="C",
            ),
            SensorColumn(
                column_name="pressure_avg",
                sensor_type="Pressure",
                sensor_direction="",
                height=10.0,
                stat_type="avg",
                unit="hPa",
            ),
        ]
        data = TimeSeriesData(df=df, sensors=sensors)

        result = calculate_air_density(data)

        assert result == STANDARD_AIR_DENSITY

    def test_sensor_column_not_in_dataframe_returns_standard(self) -> None:
        """Test that sensor column not in DataFrame returns standard."""
        df = pl.DataFrame({
            "other_column": [15.0],
        })
        sensors = [
            SensorColumn(
                column_name="temperature_avg",  # Column doesn't exist in df
                sensor_type="Temperature",
                sensor_direction="",
                height=10.0,
                stat_type="avg",
                unit="C",
            ),
            SensorColumn(
                column_name="pressure_avg",  # Column doesn't exist in df
                sensor_type="Pressure",
                sensor_direction="",
                height=10.0,
                stat_type="avg",
                unit="hPa",
            ),
        ]
        data = TimeSeriesData(df=df, sensors=sensors)

        result = calculate_air_density(data)

        assert result == STANDARD_AIR_DENSITY

    def test_different_heights(self) -> None:
        """Test with temperature and pressure at different heights."""
        data = self._create_test_data(
            temp_values=[20.0],
            pressure_values=[1010.0],
            temp_height=10.0,
            pressure_height=2.0,
        )

        result = calculate_air_density(data)

        # ρ = P / (R * T) = 101000 / (287.05 * 293.15) ≈ 1.199
        assert result > 0
        assert result != STANDARD_AIR_DENSITY


class TestConvertToStandardAirDensity:
    """Tests for convert_to_standard_air_density function."""

    def test_standard_density_returns_same_value(self) -> None:
        """Test that standard air density returns the same wind speed."""
        wind_speed = 10.0
        result = convert_to_standard_air_density(wind_speed, STANDARD_AIR_DENSITY)
        assert result == wind_speed

    def test_non_standard_density_scales_correctly(self) -> None:
        """Test conversion with non-standard air density."""
        wind_speed = 10.0
        actual_density = 1.189
        result = convert_to_standard_air_density(wind_speed, actual_density)
        expected = 10.0 * (1.189 / 1.225) ** 0.5
        assert pytest.approx(result, rel=1e-6) == expected


class TestCalculateAirDensityForHeight:
    """Tests for calculate_air_density_for_height function."""

    def test_same_height_returns_reference_density(self) -> None:
        """Test that same height returns reference density unchanged."""
        reference_density = 1.225
        reference_height = 70.0
        result = calculate_air_density_for_height(70.0, reference_density, reference_height)
        assert result == pytest.approx(reference_density, rel=1e-6)

    def test_higher_height_returns_lower_density(self) -> None:
        """Test that higher height returns lower air density."""
        reference_density = 1.225
        reference_height = 10.0
        result = calculate_air_density_for_height(100.0, reference_density, reference_height)
        assert result < reference_density
        assert result > 0

    def test_known_reference_values(self) -> None:
        """Test with known reference values."""
        # Extrapolate from 10m to 70m with density 1.225 at 10m
        reference_density = 1.225
        reference_height = 10.0
        target_height = 70.0
        result = calculate_air_density_for_height(
            target_height, reference_density, reference_height
        )
        # ρ = 1.225 * exp(-9.81 * 60 / (287.05 * (288.15 - 0.0065 * 10)))
        expected = 1.225 * (2.718281828459045 ** (-9.81 * 60 / (287.05 * (288.15 - 0.065))))
        assert pytest.approx(result, rel=1e-6) == expected
