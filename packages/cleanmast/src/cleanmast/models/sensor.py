"""Sensor column model - matches Julia's SensorColumn struct."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class SensorColumn(BaseModel):
    """Sensor metadata for a single measurement column.

    Matches Julia's SensorColumn struct from CleanMastProject.
    Uses snake_case in Python with auto-generated camelCase aliases for YAML/TOML.

    Attributes:
        column_name: Column name in DataFrame (e.g., "WindSpeed_100m_avg [m/s]")
        sensor_type: Type of sensor ("WindSpeed", "WindDirection", "Temperature", "Pressure")
        sensor_direction: Direction indicator ("N", "SE", "T", or "" for omnidirectional)
        height: Measurement height in meters
        stat_type: Statistic type ("avg", "min", "max", "sd")
        unit: Measurement unit ("m/s", "deg", "C", "Pa")
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,   # Accept snake_case in constructors
        validate_by_alias=True,  # Accept camelCase from YAML/TOML
    )

    column_name: str
    sensor_type: str
    sensor_direction: str
    height: float
    stat_type: str
    unit: str
