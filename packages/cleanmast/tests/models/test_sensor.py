"""Tests for SensorColumn model."""

import pytest
from cleanmast.models.sensor import SensorColumn


class TestSensorColumn:
    """Tests for SensorColumn Pydantic model."""

    def test_create_with_snake_case(self):
        """Test creating SensorColumn with snake_case attribute names."""
        sensor = SensorColumn(
            column_name="WindSpeed_100m_avg [m/s]",
            sensor_type="WindSpeed",
            sensor_direction="",
            height=100.0,
            stat_type="avg",
            unit="m/s",
        )

        assert sensor.column_name == "WindSpeed_100m_avg [m/s]"
        assert sensor.sensor_type == "WindSpeed"
        assert sensor.sensor_direction == ""
        assert sensor.height == 100.0
        assert sensor.stat_type == "avg"
        assert sensor.unit == "m/s"

    def test_create_from_camel_case_dict(self):
        """Test creating SensorColumn from camelCase dict (like YAML input)."""
        data = {
            "columnName": "WindDirection_80m_avg [deg]",
            "sensorType": "WindDirection",
            "sensorDirection": "N",
            "height": 80.0,
            "statType": "avg",
            "unit": "deg",
        }

        sensor = SensorColumn(**data)

        assert sensor.column_name == "WindDirection_80m_avg [deg]"
        assert sensor.sensor_type == "WindDirection"
        assert sensor.sensor_direction == "N"
        assert sensor.height == 80.0
        assert sensor.stat_type == "avg"
        assert sensor.unit == "deg"

    def test_serialize_to_camel_case(self):
        """Test serialization outputs camelCase keys for YAML compatibility."""
        sensor = SensorColumn(
            column_name="Temperature_10m_avg [C]",
            sensor_type="Temperature",
            sensor_direction="",
            height=10.0,
            stat_type="avg",
            unit="C",
        )

        # Serialize with aliases (camelCase)
        data = sensor.model_dump(by_alias=True)

        assert "columnName" in data
        assert "sensorType" in data
        assert "sensorDirection" in data
        assert "statType" in data
        assert data["columnName"] == "Temperature_10m_avg [C]"
        assert data["sensorType"] == "Temperature"

    def test_serialize_to_snake_case(self):
        """Test serialization can also output snake_case keys."""
        sensor = SensorColumn(
            column_name="Pressure_8m_avg [Pa]",
            sensor_type="Pressure",
            sensor_direction="",
            height=8.0,
            stat_type="avg",
            unit="Pa",
        )

        # Serialize without aliases (snake_case)
        data = sensor.model_dump(by_alias=False)

        assert "column_name" in data
        assert "sensor_type" in data
        assert data["column_name"] == "Pressure_8m_avg [Pa]"

    def test_wind_speed_sensor_with_direction(self):
        """Test WindSpeed sensor with directional info (e.g., tower top)."""
        sensor = SensorColumn(
            column_name="WindSpeed_140m_T_avg [m/s]",
            sensor_type="WindSpeed",
            sensor_direction="T",
            height=140.0,
            stat_type="avg",
            unit="m/s",
        )

        assert sensor.sensor_direction == "T"
        assert sensor.height == 140.0

    def test_different_stat_types(self):
        """Test sensors with different stat types."""
        for stat_type in ["avg", "min", "max", "sd"]:
            sensor = SensorColumn(
                column_name=f"WindSpeed_100m_{stat_type} [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type=stat_type,
                unit="m/s",
            )
            assert sensor.stat_type == stat_type

    def test_height_as_float(self):
        """Test that height is stored as float."""
        sensor = SensorColumn(
            column_name="WindSpeed_100m_avg [m/s]",
            sensor_type="WindSpeed",
            sensor_direction="",
            height=100,  # Integer input
            stat_type="avg",
            unit="m/s",
        )

        assert isinstance(sensor.height, float)
        assert sensor.height == 100.0

    def test_missing_required_field_raises_error(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            SensorColumn(
                column_name="WindSpeed_100m_avg [m/s]",
                # Missing sensor_type and other required fields
            )
