"""Tests for wind rose builder schema import correctness — reporting domain.

Ported from tests/assessment/wind_rose/test_wind_rose_builder_schema_import.py.
Test logic preserved exactly.
"""

import inspect

import polars as pl
from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
from cleanmast.subdomains.reporting.subdomains.wind_rose.compute import (
    calculate_wind_rose,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.schemas import (
    WindRoseSchema as CorrectWindRoseSchema,
)


class TestWindRoseBuilderSchemaImport:
    """Tests that wind_rose assemble uses the correct schema."""

    def test_wind_rose_assemble_uses_correct_schema_class(self) -> None:
        """Verify assemble uses WindRoseSchema from model/schemas.py."""
        import cleanmast.subdomains.reporting.subdomains.wind_rose.assemble as builder_module

        source_file = inspect.getfile(builder_module)
        with open(source_file, encoding="utf-8") as f:
            source_code = f.read()

        assert "wind_rose.model.schemas" in source_code, (
            "assemble.py must import WindRoseSchema from wind_rose.model.schemas"
        )

    def test_wind_rose_calculator_uses_correct_schema_class(self) -> None:
        """Verify compute imports from the correct module."""
        import cleanmast.subdomains.reporting.subdomains.wind_rose.compute as calculator_module

        source_file = inspect.getfile(calculator_module)
        with open(source_file, encoding="utf-8") as f:
            source_code = f.read()

        # compute.py is pure functions, no schema import needed
        # Just verify it uses SECTOR_LABELS constant
        assert "SECTOR_LABELS" in source_code
        assert "SECTOR_COUNT" in source_code

    def test_correct_schema_has_9_columns(self) -> None:
        """Verify the correct schema has 9 columns including month and month_name."""
        correct_columns = set(CorrectWindRoseSchema.columns().keys())

        expected_columns = {
            "month",
            "month_name",
            "sector",
            "sector_name",
            "height",
            "interpolation_marker",
            "frequency",
            "wind_power_density",
            "energy_frequency",
        }

        assert correct_columns == expected_columns, (
            f"Correct WindRoseSchema should have 9 columns: {expected_columns}, "
            f"but got: {correct_columns}"
        )


class TestWindRoseCalculatorMonthColumns:
    """Tests that calculate_wind_rose produces DataFrame with month columns."""

    def _create_test_input(
        self,
        wind_speeds: list[float],
        wind_directions: list[float],
        timestamps: list[str] | None = None,
        height: float = 100.0,
    ) -> TimeSeriesData:
        if timestamps is None:
            timestamps = [f"2024-01-{i:02d}T00:00:00" for i in range(1, len(wind_speeds) + 1)]

        df = pl.DataFrame({
            "timestamp": pl.Series(timestamps).str.to_datetime(),
            "WS_100m_avg": wind_speeds,
            "WD_100m_avg": wind_directions,
        })

        sensors = [
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=height,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_100m_avg",
                sensor_type="WindDirection",
                sensor_direction="",
                height=height,
                stat_type="avg",
                unit="deg",
            ),
        ]

        return TimeSeriesData(df=df, sensors=sensors)

    def test_calculator_produces_month_column(self) -> None:
        """Verify calculator output includes 'month' column."""
        timestamps = []
        wind_speeds = []
        wind_directions = []
        for month in range(1, 4):
            for day in range(1, 6):
                timestamps.append(f"2024-{month:02d}-{day:02d}T00:00:00")
                wind_speeds.append(5.0)
                wind_directions.append(float((month * day * 10) % 360))

        input_data = self._create_test_input(
            wind_speeds=wind_speeds,
            wind_directions=wind_directions,
            timestamps=timestamps,
        )

        result = calculate_wind_rose(input_data, air_density=1.225, heights=[100.0])

        assert "month" in result.columns

    def test_calculator_produces_month_name_column(self) -> None:
        """Verify calculator output includes 'month_name' column."""
        timestamps = []
        wind_speeds = []
        wind_directions = []
        for month in range(1, 4):
            for day in range(1, 6):
                timestamps.append(f"2024-{month:02d}-{day:02d}T00:00:00")
                wind_speeds.append(5.0)
                wind_directions.append(float((month * day * 10) % 360))

        input_data = self._create_test_input(
            wind_speeds=wind_speeds,
            wind_directions=wind_directions,
            timestamps=timestamps,
        )

        result = calculate_wind_rose(input_data, air_density=1.225, heights=[100.0])

        assert "month_name" in result.columns

    def test_calculator_produces_all_9_columns(self) -> None:
        """Verify calculator produces all 9 columns matching CorrectWindRoseSchema."""
        timestamps = []
        wind_speeds = []
        wind_directions = []
        for month in range(1, 4):
            for day in range(1, 6):
                timestamps.append(f"2024-{month:02d}-{day:02d}T00:00:00")
                wind_speeds.append(5.0)
                wind_directions.append(float((month * day * 10) % 360))

        input_data = self._create_test_input(
            wind_speeds=wind_speeds,
            wind_directions=wind_directions,
            timestamps=timestamps,
        )

        result = calculate_wind_rose(input_data, air_density=1.225, heights=[100.0])

        expected_columns = {
            "month",
            "month_name",
            "sector",
            "sector_name",
            "height",
            "interpolation_marker",
            "frequency",
            "wind_power_density",
            "energy_frequency",
        }

        actual_columns = set(result.columns)

        assert actual_columns == expected_columns, (
            f"Expected columns: {expected_columns}, but got: {actual_columns}"
        )
