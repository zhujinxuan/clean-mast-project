"""Tests for fill_heights helper functions."""

import numpy as np
import pytest
from cleanmast.shared.timeseries import SensorColumn
from cleanmast.subdomains.dataprocessing.services.height_filling.helpers import (
    calculate_interpolation_weights,
    degrees_to_vector,
    find_neighbor_sensors,
    generate_target_column,
    get_existing_sensors,
    get_sensor_for_height,
    vector_to_degrees,
)


class TestGetExistingSensors:
    """Tests for get_existing_sensors function."""

    def test_get_existing_sensors_filters_by_type(self, sample_sensor_columns: list[SensorColumn]):
        """Test that sensors are filtered by sensor type."""
        ws_sensors = get_existing_sensors(sample_sensor_columns, "WindSpeed")
        wd_sensors = get_existing_sensors(sample_sensor_columns, "WindDirection")

        assert [s.height for s in ws_sensors] == [50.0, 80.0, 100.0]
        assert [s.height for s in wd_sensors] == [50.0, 80.0, 100.0]

    def test_get_existing_sensors_only_avg(self, sample_sensor_columns: list[SensorColumn]):
        """Test that only 'avg' stat_type sensors are included."""
        ws_sensors = get_existing_sensors(sample_sensor_columns, "WindSpeed")

        # Should only have 3 sensors (not the max sensor at 80m)
        assert len(ws_sensors) == 3
        assert any(s.height == 80.0 for s in ws_sensors)  # The avg sensor, not max

    def test_get_existing_sensors_returns_sorted(self, sample_sensor_columns: list[SensorColumn]):
        """Test that returned sensors are sorted by height in ascending order."""
        sensors = get_existing_sensors(sample_sensor_columns, "WindSpeed")
        heights = [s.height for s in sensors]

        assert heights == sorted(heights)
        assert heights[0] < heights[1] < heights[2]


class TestGenerateTargetColumn:
    """Tests for generate_target_column function."""

    def test_generate_target_column_ws(self):
        """Test generating WS target column names."""
        interpolated = generate_target_column("WindSpeed", 120.0, "interpolated")
        extrapolated = generate_target_column("WindSpeed", 160.0, "extrapolated")

        assert interpolated == "WS_120m_fill:interpolated"
        assert extrapolated == "WS_160m_fill:extrapolated"

    def test_generate_target_column_wd(self):
        """Test generating WD target column names."""
        interpolated = generate_target_column("WindDirection", 90.0, "interpolated")
        extrapolated = generate_target_column("WindDirection", 150.0, "extrapolated")

        assert interpolated == "WD_90m_fill:interpolated"
        assert extrapolated == "WD_150m_fill:extrapolated"

    def test_generate_target_column_decimal_height(self):
        """Test generating column names with decimal heights."""
        col = generate_target_column("WindSpeed", 76.5, "interpolated")

        assert col == "WS_76m_fill:interpolated"


class TestFindNeighborSensors:
    """Tests for find_neighbor_sensors function."""

    @staticmethod
    def _make_ws_sensors(heights: list[float]) -> list[SensorColumn]:
        """Helper to create WS sensor list from heights."""
        return [
            SensorColumn(
                column_name=f"WS_{int(h)}m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=h,
                stat_type="avg",
                unit="m/s",
            )
            for h in heights
        ]

    def test_find_neighbor_sensors_finds_correct_pair(self):
        """Test finding neighbors for a target within range."""
        sensors = self._make_ws_sensors([50.0, 80.0, 100.0])

        lower, higher = find_neighbor_sensors(65.0, sensors)
        assert lower.height == 50.0
        assert higher.height == 80.0

        lower, higher = find_neighbor_sensors(90.0, sensors)
        assert lower.height == 80.0
        assert higher.height == 100.0

    def test_find_neighbor_sensors_at_midpoint(self):
        """Test finding neighbors at exact midpoint."""
        sensors = self._make_ws_sensors([50.0, 80.0, 100.0])

        lower, higher = find_neighbor_sensors(75.0, sensors)
        assert lower.height == 50.0
        assert higher.height == 80.0

    def test_find_neighbor_sensors_raises_on_edge(self):
        """Test that ValueError is raised for edge cases."""
        sensors = self._make_ws_sensors([50.0, 80.0, 100.0])

        # Below minimum
        with pytest.raises(ValueError, match="Cannot find neighbors"):
            find_neighbor_sensors(40.0, sensors)

        # Above maximum
        with pytest.raises(ValueError, match="Cannot find neighbors"):
            find_neighbor_sensors(110.0, sensors)

        # Exactly at a sensor height - finds surrounding neighbors
        # (not an error condition - useful for interpolation)
        lower, higher = find_neighbor_sensors(80.0, sensors)
        assert lower.height == 50.0
        assert higher.height == 100.0


class TestCalculateInterpolationWeights:
    """Tests for calculate_interpolation_weights function."""

    def test_calculate_interpolation_weights_sum_to_one(self):
        """Test that calculated weights always sum to 1.0."""
        test_cases = [
            (65.0, 50.0, 80.0),  # 2:1 ratio
            (75.0, 50.0, 100.0),  # Midpoint
            (60.0, 50.0, 80.0),  # Close to lower
            (78.0, 50.0, 80.0),  # Close to higher
        ]

        for target, lower, higher in test_cases:
            w_low, w_high = calculate_interpolation_weights(target, lower, higher)
            total = w_low + w_high
            assert abs(total - 1.0) < 1e-10, f"Weights sum to {total} for target={target}"

    def test_calculate_interpolation_weights_inverse_distance(self):
        """Test that weights are inversely proportional to distance."""
        # Midpoint: should have equal weights
        w_low, w_high = calculate_interpolation_weights(65.0, 50.0, 80.0)
        assert abs(w_low - w_high) < 0.01

        # Closer to lower: higher weight on lower
        w_low, w_high = calculate_interpolation_weights(55.0, 50.0, 80.0)
        assert w_low > w_high

        # Closer to higher: higher weight on higher
        w_low, w_high = calculate_interpolation_weights(75.0, 50.0, 80.0)
        assert w_high > w_low


class TestGetSensorForHeight:
    """Tests for get_sensor_for_height function."""

    def test_get_sensor_for_height_finds_correct_sensor(self, sample_sensor_columns: list[SensorColumn]):
        """Test finding sensor for given sensor type and height."""
        sensor_50m_ws = get_sensor_for_height(sample_sensor_columns, "WindSpeed", 50.0)
        sensor_80m_ws = get_sensor_for_height(sample_sensor_columns, "WindSpeed", 80.0)
        sensor_100m_ws = get_sensor_for_height(sample_sensor_columns, "WindSpeed", 100.0)

        assert sensor_50m_ws is not None
        assert sensor_50m_ws.column_name == "WS_50m_avg"
        assert sensor_80m_ws is not None
        assert sensor_80m_ws.column_name == "WS_80m_avg"
        assert sensor_100m_ws is not None
        assert sensor_100m_ws.column_name == "WS_100m_avg"

        sensor_50m_wd = get_sensor_for_height(sample_sensor_columns, "WindDirection", 50.0)
        assert sensor_50m_wd is not None
        assert sensor_50m_wd.column_name == "WD_50m_avg"

    def test_get_sensor_for_height_returns_none_when_not_found(self, sample_sensor_columns: list[SensorColumn]):
        """Test that None is returned when sensor not found."""
        result = get_sensor_for_height(sample_sensor_columns, "WindSpeed", 200.0)
        assert result is None

        result = get_sensor_for_height(sample_sensor_columns, "WindDirection", 30.0)
        assert result is None

    def test_get_sensor_for_height_only_avg(self, sample_sensor_columns: list[SensorColumn]):
        """Test that only 'avg' stat_type sensors are matched."""
        # 80m avg sensor exists
        sensor = get_sensor_for_height(sample_sensor_columns, "WindSpeed", 80.0)
        assert sensor is not None
        assert sensor.column_name == "WS_80m_avg"

        # But there's no avg sensor at 30m
        result = get_sensor_for_height(sample_sensor_columns, "WindSpeed", 30.0)
        assert result is None


class TestDegreesToVector:
    """Tests for degrees_to_vector function."""

    def test_degrees_to_vector_converts_correctly(self):
        """Test conversion from degrees to vector components."""
        # North (0°): wind FROM north, so vector points south
        u, v = degrees_to_vector(0.0)
        assert abs(u) < 1e-10  # u should be ~0
        assert abs(v + 1.0) < 1e-10  # v should be -1 (south)

        # East (90°): wind FROM east, vector points west
        u, v = degrees_to_vector(90.0)
        assert abs(u + 1.0) < 1e-10  # u should be -1 (west)
        assert abs(v) < 1e-10  # v should be ~0

        # South (180°): wind FROM south, vector points north
        u, v = degrees_to_vector(180.0)
        assert abs(u) < 1e-10
        assert abs(v - 1.0) < 1e-10  # v should be +1 (north)

        # West (270°): wind FROM west, vector points east
        u, v = degrees_to_vector(270.0)
        assert abs(u - 1.0) < 1e-10  # u should be +1 (east)
        assert abs(v) < 1e-10

    def test_degrees_to_vector_unit_length(self):
        """Test that vector components produce unit length."""
        test_angles = [0, 45, 90, 135, 180, 225, 270, 315, 355, 5]

        for angle in test_angles:
            u, v = degrees_to_vector(angle)
            length = np.sqrt(u**2 + v**2)
            assert abs(length - 1.0) < 1e-10, f"Length is {length} for angle {angle}"


class TestVectorToDegrees:
    """Tests for vector_to_degrees function."""

    def test_vector_to_degrees_round_trip(self):
        """Test that degrees -> vector -> degrees round-trips correctly."""
        test_angles = [0, 45, 90, 135, 180, 225, 270, 315, 355, 5, 359]

        for original in test_angles:
            u, v = degrees_to_vector(original)
            recovered = vector_to_degrees(u, v)
            diff = abs(recovered - original)
            # Handle 360/0 wrap
            if diff > 180:
                diff = 360 - diff
            assert diff < 1e-10, f"Failed for {original}: got {recovered}"

    def test_vector_to_degrees_cardinal_directions(self):
        """Test conversion for cardinal directions using meteorological convention."""
        # Note: meteorological convention - direction FROM which wind blows
        # Wind FROM North: vector points South (0, -1) -> direction = 0°
        # Wind FROM East: vector points West (-1, 0) -> direction = 90°
        # Wind FROM South: vector points North (0, 1) -> direction = 180°
        # Wind FROM West: vector points East (1, 0) -> direction = 270°

        # Wind FROM North (0°): vector points South (0, -1)
        deg = vector_to_degrees(0.0, -1.0)
        assert abs(deg - 0.0) < 1e-10 or abs(deg - 360.0) < 1e-10

        # Wind FROM East (90°): vector points West (-1, 0)
        deg = vector_to_degrees(-1.0, 0.0)
        assert abs(deg - 90.0) < 1e-10

        # Wind FROM South (180°): vector points North (0, 1)
        deg = vector_to_degrees(0.0, 1.0)
        assert abs(deg - 180.0) < 1e-10

        # Wind FROM West (270°): vector points East (1, 0)
        deg = vector_to_degrees(1.0, 0.0)
        assert abs(deg - 270.0) < 1e-10

    def test_vector_to_degrees_range(self):
        """Test that result is always in [0, 360)."""
        test_vectors = [
            (1.0, 0.0),
            (-1.0, 0.0),
            (0.0, 1.0),
            (0.0, -1.0),
            (0.5, 0.5),
            (-0.5, -0.5),
        ]

        for u, v in test_vectors:
            deg = vector_to_degrees(u, v)
            assert 0.0 <= deg < 360.0, f"Degrees {deg} out of range for ({u}, {v})"
