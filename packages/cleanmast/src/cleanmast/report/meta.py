"""Metadata and helper functions for report generation."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

# Constants for air density calculation
GAS_CONSTANT_DRY_AIR = 287.05  # J/(kg·K), specific gas constant for dry air
STANDARD_AIR_DENSITY = 1.225  # kg/m³ at 15°C and 1013.25 hPa
KELVIN_OFFSET = 273.15  # Conversion from Celsius to Kelvin
HPA_TO_PA = 100  # Conversion from hectopascals to pascals
PA_TO_HPA = 0.01  # Conversion from pascals to hectopascals

FILL_TYPE_PATTERN = r"_fill:(\w+)$"

# Chinese display labels for fill types
FILL_TYPE_LABELS: dict[str, str] = {
    "extrapolated": "外推",
    "interpolated": "内插",
}

# Temperature and pressure column patterns
TEMPERATURE_PATTERNS = [
    r".*temperature.*",
    r".*analog.*c\s*\[.*°?c.*\].*",
    r"Analog_\d+m.*C",
]

PRESSURE_PATTERNS = [
    r".*pressure.*",
    r".*kpa.*",
    r"Analog_\d+m.*KPA",
    r".*barom.*",
]


@dataclass
class SingleMastMeta:
    """Metadata for single mast report atoms."""
    mast_name: str
    air_density: float = 1.225  # Calculated in recommend phase
    caption: str = ""
    width: str = "80%"


def detect_interpolation_marker(column_name: str) -> str:
    """Detect fill type marker from column name.
    
    Returns Chinese label:
    - "外推" for extrapolated (extrapolated)
    - "内插" for interpolated (interpolated)
    - Empty string if no fill marker found (original measured data)
    
    Pattern: *_fill:{type} at end of column name
    """
    if match := re.search(FILL_TYPE_PATTERN, column_name, re.IGNORECASE):
        fill_type = match.group(1).lower()
        return FILL_TYPE_LABELS.get(fill_type, "")
    return ""


def get_height_display_name(height: float, marker: str = "") -> str:
    """Generate display name for a height level.
    
    Args:
        height: Height value in meters
        marker: Interpolation/extrapolation marker (e.g., "外推", "内插")
    
    Returns:
        Formatted display name like "125m 外推" or "100m"
    """
    base = f"{int(height)}m"
    if marker:
        return f"{base} {marker}"
    return base


def _find_temperature_column(columns: list[str]) -> str | None:
    """Find temperature column from list of column names."""
    for col in columns:
        col_lower = col.lower()
        for pattern in TEMPERATURE_PATTERNS:
            if re.search(pattern, col_lower, re.IGNORECASE):
                return col
    return None


def _find_pressure_column(columns: list[str]) -> str | None:
    """Find pressure column from list of column names."""
    for col in columns:
        col_lower = col.lower()
        for pattern in PRESSURE_PATTERNS:
            if re.search(pattern, col_lower, re.IGNORECASE):
                return col
    return None


def _normalize_temperature(temp_value: float) -> float:
    """Normalize temperature to Kelvin.
    
    If value is below 100, assumes Celsius and converts to Kelvin.
    If value is 100 or above, assumes already in Kelvin.
    """
    if temp_value < 100:
        # Celsius to Kelvin
        return temp_value + KELVIN_OFFSET
    return temp_value


def _normalize_pressure(pressure_value: float) -> float:
    """Normalize pressure to Pascals.
    
    If value is below 10000, assumes hPa and converts to Pa.
    If value is 10000 or above, assumes already in Pa.
    """
    if pressure_value < 10000:
        # hPa to Pa
        return pressure_value * HPA_TO_PA
    return pressure_value


def calculate_air_density(
    df: pl.DataFrame,
    temp_col: str | None = None,
    pressure_col: str | None = None,
) -> float:
    """Calculate air density from temperature and pressure data.
    
    Uses the ideal gas law: ρ = P / (R * T)
    where:
    - ρ = air density (kg/m³)
    - P = pressure (Pa)
    - R = specific gas constant for dry air (287.05 J/(kg·K))
    - T = temperature (K)
    
    Args:
        df: DataFrame containing meteorological data
        temp_col: Column name for temperature. If None, auto-detected.
        pressure_col: Column name for pressure. If None, auto-detected.
    
    Returns:
        Average air density (kg/m³). Returns 1.225 if temp/pressure not found.
    """
    columns = df.columns
    
    # Auto-detect columns if not provided
    if temp_col is None:
        temp_col = _find_temperature_column(columns)
    if pressure_col is None:
        pressure_col = _find_pressure_column(columns)
    
    # Fallback to standard air density if columns not found
    if temp_col is None or pressure_col is None:
        return STANDARD_AIR_DENSITY
    
    # Validate columns exist
    if temp_col not in columns or pressure_col not in columns:
        return STANDARD_AIR_DENSITY
    
    try:
        # Get mean values, handling missing data
        temp_mean = df[temp_col].mean()
        pressure_mean = df[pressure_col].mean()
        
        # Check for valid values
        if temp_mean is None or pressure_mean is None:
            return STANDARD_AIR_DENSITY
        
        # Normalize units - cast polars scalar to float
        temp_k = _normalize_temperature(float(temp_mean))  # type: ignore[arg-type]
        pressure_pa = _normalize_pressure(float(pressure_mean))  # type: ignore[arg-type]
        
        # Calculate air density using ideal gas law
        air_density = pressure_pa / (GAS_CONSTANT_DRY_AIR * temp_k)
        
        return air_density
    except (TypeError, ValueError, ZeroDivisionError):
        # Return standard value on any calculation error
        return STANDARD_AIR_DENSITY
