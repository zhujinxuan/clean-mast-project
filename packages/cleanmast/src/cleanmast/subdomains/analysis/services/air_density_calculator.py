"""Air density calculator domain service.

ADR-GUARDRAILS: domain-001-sensor-access, data-001-symbol-columns, structure-001-subdomain-layout
Compliance: Domain Service ✓ | Sensor-based access ✓ | No column name patterns ✓
Description: Domain service wrapper for air density calculation using sensor metadata
"""

from cleanmast.subdomains.analysis.value_objects.air_density import calculate_air_density
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData


class AirDensityCalculator:
    """Domain service for calculating air density from time series data.

    This service wraps the air density calculation logic from value_objects.air_density,
    providing a domain service interface that finds Temperature and Pressure sensors
    by their sensor_type metadata (NOT by column name patterns).

    Uses the ideal gas law: ρ = P / (R * T)
    where:
    - ρ = air density (kg/m³)
    - P = pressure (Pa)
    - R = specific gas constant for dry air (287.05 J/(kg·K))
    - T = temperature (K)
    """

    def calculate(self, data: TimeSeriesData) -> float:
        """Calculate average air density from temperature and pressure data.

        Finds Temperature and Pressure sensors by their sensor_type metadata
        and calculates the average air density using the ideal gas law.

        Args:
            data: TimeSeriesData containing DataFrame and sensor metadata

        Returns:
            Average air density in kg/m³. Returns 1.225 (standard air density)
            if temperature or pressure sensors are not found or calculation fails.
        """
        return calculate_air_density(data)
