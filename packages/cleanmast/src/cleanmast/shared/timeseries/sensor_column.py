"""Sensor column value object - matches Julia's SensorColumn struct.

Description: Value object representing sensor metadata with Julia-compatible camelCase serialization
"""

import re

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

    def detect_interpolation_marker(self) -> str:
        """Detect fill type marker from column name.

        Returns Chinese label:
        - "外推" for extrapolated
        - "内插" for interpolated
        - Empty string if no fill marker found (original measured data)

        Pattern: *_fill:{type} at end of column name
        """
        FILL_TYPE_PATTERN = r"_fill:(\w+)$"
        FILL_TYPE_LABELS: dict[str, str] = {
            "extrapolated": "外推",
            "interpolated": "内插",
        }
        if match := re.search(FILL_TYPE_PATTERN, self.column_name, re.IGNORECASE):
            fill_type = match.group(1).lower()
            return FILL_TYPE_LABELS.get(fill_type, "")
        return ""
