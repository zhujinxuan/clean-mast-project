"""Tests for report meta module."""

import polars as pl
import pytest

from cleanmast.report.meta import (
    FILL_TYPE_LABELS,
    GAS_CONSTANT_DRY_AIR,
    STANDARD_AIR_DENSITY,
    SingleMastMeta,
    calculate_air_density,
    detect_interpolation_marker,
    get_height_display_name,
    _find_temperature_column,
    _find_pressure_column,
    _normalize_temperature,
    _normalize_pressure,
)


class TestSingleMastMeta:
    """Tests for SingleMastMeta dataclass."""

    def test_default_values(self):
        """Test that SingleMastMeta has correct default values."""
        meta = SingleMastMeta(mast_name="M01")

        assert meta.mast_name == "M01"
        assert meta.air_density == 1.225  # Default value
        assert meta.caption == ""
        assert meta.width == "80%"

    def test_custom_values(self):
        """Test that SingleMastMeta accepts custom values."""
        meta = SingleMastMeta(
            mast_name="M02",
            air_density=1.18,
            caption="Test Caption",
            width="90%",
        )

        assert meta.mast_name == "M02"
        assert meta.air_density == 1.18
        assert meta.caption == "Test Caption"
        assert meta.width == "90%"


class TestDetectInterpolationMarker:
    """Tests for detect_interpolation_marker function."""

    def test_extrapolated_marker(self):
        """Test detection of extrapolated marker."""
        result = detect_interpolation_marker("WS_120m_fill:extrapolated")

        assert result == "外推"

    def test_interpolated_marker(self):
        """Test detection of interpolated marker."""
        result = detect_interpolation_marker("WS_90m_fill:interpolated")

        assert result == "内插"

    def test_no_marker(self):
        """Test with no fill marker."""
        result = detect_interpolation_marker("WS_100m_avg")

        assert result == ""

    def test_unknown_marker(self):
        """Test with unknown fill type."""
        result = detect_interpolation_marker("WS_100m_fill:unknown")

        assert result == ""  # Returns empty string for unknown types

    def test_case_insensitive(self):
        """Test that detection is case insensitive."""
        result1 = detect_interpolation_marker("WS_100m_fill:EXTRAPOLATED")
        result2 = detect_interpolation_marker("WS_100m_fill:Extrapolated")

        assert result1 == "外推"
        assert result2 == "外推"


class TestGetHeightDisplayName:
    """Tests for get_height_display_name function."""

    def test_without_marker(self):
        """Test display name without marker."""
        result = get_height_display_name(100.0)

        assert result == "100m"

    def test_with_extrapolated_marker(self):
        """Test display name with extrapolation marker."""
        result = get_height_display_name(120.0, "外推")

        assert result == "120m 外推"

    def test_with_interpolated_marker(self):
        """Test display name with interpolation marker."""
        result = get_height_display_name(90.0, "内插")

        assert result == "90m 内插"

    def test_float_height_converted_to_int(self):
        """Test that float heights are displayed as integers."""
        result = get_height_display_name(100.7)

        assert result == "100m"


class TestFindTemperatureColumn:
    """Tests for _find_temperature_column helper."""

    def test_find_temperature_pattern(self):
        """Test finding temperature column with various patterns."""
        columns = ["temperature_avg", "pressure_avg", "ws_avg"]
        result = _find_temperature_column(columns)
        assert result == "temperature_avg"

    def test_find_analog_pattern(self):
        """Test finding temperature column with analog pattern."""
        columns = ["Analog_10m_C", "pressure_avg"]
        result = _find_temperature_column(columns)
        assert result == "Analog_10m_C"

    def test_no_temperature_column(self):
        """Test when no temperature column exists."""
        columns = ["pressure", "ws_avg"]
        result = _find_temperature_column(columns)
        assert result is None


class TestFindPressureColumn:
    """Tests for _find_pressure_column helper."""

    def test_find_pressure_pattern(self):
        """Test finding pressure column with various patterns."""
        columns = ["pressure_avg", "temperature_avg"]
        result = _find_pressure_column(columns)
        assert result == "pressure_avg"

    def test_find_kpa_pattern(self):
        """Test finding pressure column with kPa pattern."""
        columns = ["Analog_10m_KPA", "ws_avg"]
        result = _find_pressure_column(columns)
        assert result == "Analog_10m_KPA"

    def test_find_barom_pattern(self):
        """Test finding pressure column with barom pattern."""
        columns = ["barometer", "ws_avg"]
        result = _find_pressure_column(columns)
        assert result == "barometer"

    def test_no_pressure_column(self):
        """Test when no pressure column exists."""
        columns = ["temperature", "ws_avg"]
        result = _find_pressure_column(columns)
        assert result is None


class TestNormalizeTemperature:
    """Tests for _normalize_temperature helper."""

    def test_celsius_to_kelvin(self):
        """Test conversion from Celsius to Kelvin."""
        result = _normalize_temperature(15.0)
        assert result == 288.15  # 15 + 273.15

    def test_already_kelvin(self):
        """Test that Kelvin values are returned unchanged."""
        result = _normalize_temperature(300.0)
        assert result == 300.0

    def test_boundary_at_100(self):
        """Test boundary condition at 100 degrees."""
        # 100 should be treated as Kelvin (below 100 is Celsius)
        result = _normalize_temperature(100.0)
        assert result == 100.0


class TestNormalizePressure:
    """Tests for _normalize_pressure helper."""

    def test_hpa_to_pa(self):
        """Test conversion from hPa to Pa."""
        result = _normalize_pressure(1013.25)
        assert result == 101325.0  # 1013.25 * 100

    def test_already_pa(self):
        """Test that Pa values are returned unchanged."""
        result = _normalize_pressure(101325.0)
        assert result == 101325.0

    def test_boundary_at_10000(self):
        """Test boundary condition at 10000 Pa."""
        result = _normalize_pressure(10000.0)
        assert result == 10000.0


class TestCalculateAirDensity:
    """Tests for calculate_air_density function."""

    def test_with_valid_data(self):
        """Test calculation with valid temperature and pressure."""
        df = pl.DataFrame({
            "temperature": [15.0, 16.0, 14.0],  # Celsius
            "pressure": [1013.25, 1014.0, 1012.0],  # hPa
        })

        result = calculate_air_density(df, "temperature", "pressure")

        # Expected: ρ = P / (R * T)
        # T_avg = 15°C = 288.15 K
        # P_avg = 1013.083... hPa = 101308.3 Pa
        # ρ = 101308.3 / (287.05 * 288.15) ≈ 1.225
        assert pytest.approx(result, rel=0.01) == 1.225

    def test_auto_detect_columns(self):
        """Test auto-detection of temperature and pressure columns."""
        df = pl.DataFrame({
            "temperature_avg": [15.0],
            "pressure_avg": [1013.25],
        })

        result = calculate_air_density(df)

        assert result != STANDARD_AIR_DENSITY
        assert result > 0

    def test_missing_columns_returns_standard(self):
        """Test that missing columns return standard air density."""
        df = pl.DataFrame({
            "ws_avg": [5.0],
        })

        result = calculate_air_density(df)

        assert result == STANDARD_AIR_DENSITY

    def test_invalid_column_names_returns_standard(self):
        """Test that invalid column names return standard air density."""
        df = pl.DataFrame({
            "temperature": [15.0],
            "pressure": [1013.25],
        })

        result = calculate_air_density(df, "temp", "pres")

        assert result == STANDARD_AIR_DENSITY

    def test_none_values_returns_standard(self):
        """Test that None mean values return standard air density."""
        df = pl.DataFrame({
            "temperature": [None, None],
            "pressure": [None, None],
        })

        result = calculate_air_density(df, "temperature", "pressure")

        assert result == STANDARD_AIR_DENSITY

    def test_calculation_error_returns_standard(self):
        """Test that calculation errors return standard air density."""
        df = pl.DataFrame({
            "temperature": [],  # Empty - will cause None mean
            "pressure": [],
        })

        result = calculate_air_density(df, "temperature", "pressure")

        assert result == STANDARD_AIR_DENSITY


class TestConstants:
    """Tests for module constants."""

    def test_gas_constant_value(self):
        """Test gas constant has correct value."""
        assert GAS_CONSTANT_DRY_AIR == 287.05

    def test_standard_air_density_value(self):
        """Test standard air density has correct value."""
        assert STANDARD_AIR_DENSITY == 1.225

    def test_fill_type_labels(self):
        """Test fill type labels dictionary."""
        assert FILL_TYPE_LABELS["extrapolated"] == "外推"
        assert FILL_TYPE_LABELS["interpolated"] == "内插"
