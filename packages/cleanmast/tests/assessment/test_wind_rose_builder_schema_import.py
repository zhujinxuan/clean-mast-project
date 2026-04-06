"""Tests for wind rose builder schema import correctness.

RED phase tests: These tests verify that wind_rose_builder uses the correct
WindRoseSchema from single_mast/schemas.py (8 columns with month/month_name),
NOT from value_objects/schemas.py (6 columns without month).
"""

import inspect

import polars as pl
from cleanmast.subdomains.assessment.domain.services.calculators.wind_rose_calculator import (
    WindRoseCalculator,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.assessment.domain.value_objects.schemas import (
    WindRoseSchema as WrongWindRoseSchema,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WindRoseSchema as CorrectWindRoseSchema,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


class TestWindRoseBuilderSchemaImport:
    """Tests that wind_rose_builder imports from the correct module."""

    def test_wind_rose_builder_uses_correct_schema_class(self) -> None:
        """Verify builder uses WindRoseSchema from single_mast/schemas.py.

        The builder should use the 8-column schema (with month/month_name),
        not the 6-column schema (without month).
        """
        # Get the source file of the module
        import cleanmast.subdomains.assessment.domain.services.builders.wind_rose_builder as builder_module

        source_file = inspect.getfile(builder_module)
        with open(source_file, encoding="utf-8") as f:
            source_code = f.read()

        # Should import from single_mast.schemas, NOT value_objects.schemas
        assert "value_objects.single_mast.schemas" in source_code, (
            "wind_rose_builder.py must import WindRoseSchema from single_mast.schemas, "
            "not from value_objects.schemas"
        )
        assert "from cleanmast.subdomains.assessment.domain.value_objects.schemas import WindRoseSchema" not in source_code, (
            "wind_rose_builder.py incorrectly imports from value_objects.schemas "
            "(the 6-column schema without month/month_name)"
        )

    def test_wind_rose_calculator_uses_correct_schema_class(self) -> None:
        """Verify calculator uses WindRoseSchema from single_mast/schemas.py."""
        import cleanmast.subdomains.assessment.domain.services.calculators.wind_rose_calculator as calculator_module

        source_file = inspect.getfile(calculator_module)
        with open(source_file, encoding="utf-8") as f:
            source_code = f.read()

        # Should import from single_mast.schemas
        assert "value_objects.single_mast.schemas" in source_code, (
            "wind_rose_calculator.py must import WindRoseSchema from single_mast.schemas"
        )

    def test_correct_schema_has_8_columns(self) -> None:
        """Verify the correct schema has 8 columns including month and month_name."""
        # Get column names from the correct schema class
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
        }

        assert correct_columns == expected_columns, (
            f"Correct WindRoseSchema should have 8 columns: {expected_columns}, "
            f"but got: {correct_columns}"
        )

    def test_wrong_schema_has_6_columns(self) -> None:
        """Verify the wrong schema has 6 columns (no month/month_name)."""
        wrong_columns = set(WrongWindRoseSchema.columns().keys())

        expected_wrong_columns = {
            "sector",
            "sector_name",
            "height",
            "interpolation_marker",
            "frequency",
            "wind_power_density",
        }

        assert wrong_columns == expected_wrong_columns, (
            f"Wrong WindRoseSchema should have 6 columns: {expected_wrong_columns}, "
            f"but got: {wrong_columns}"
        )

    def test_schemas_are_different(self) -> None:
        """Verify the two schemas are actually different classes."""
        assert CorrectWindRoseSchema is not WrongWindRoseSchema, (
            "The two schemas should be different classes"
        )

        correct_columns = set(CorrectWindRoseSchema.columns().keys())
        wrong_columns = set(WrongWindRoseSchema.columns().keys())

        assert "month" in correct_columns and "month" not in wrong_columns
        assert "month_name" in correct_columns and "month_name" not in wrong_columns


class TestWindRoseCalculatorMonthColumns:
    """Tests that wind_rose_calculator produces DataFrame with month columns."""

    def _create_test_input(
        self,
        wind_speeds: list[float],
        wind_directions: list[float],
        timestamps: list[str] | None = None,
        height: float = 100.0,
        air_density: float | None = None,
    ) -> SingleMastAnalysisInput:
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

        time_series = TimeSeriesData(df=df, sensors=sensors)
        parameters = AnalysisParameters(heights=[height], air_density=air_density)

        return SingleMastAnalysisInput(
            time_series=time_series,
            parameters=parameters,
            mast_name="TestMast",
        )

    def test_calculator_produces_month_column(self) -> None:
        """Verify calculator output includes 'month' column."""
        # Create test data spanning multiple months
        timestamps = []
        wind_speeds = []
        wind_directions = []
        for month in range(1, 4):  # Jan, Feb, Mar
            for day in range(1, 6):  # 5 days per month
                timestamps.append(f"2024-{month:02d}-{day:02d}T00:00:00")
                wind_speeds.append(5.0)
                wind_directions.append(float((month * day * 10) % 360))

        input_data = self._create_test_input(
            wind_speeds=wind_speeds,
            wind_directions=wind_directions,
            timestamps=timestamps,
            air_density=1.225,
        )

        calculator = WindRoseCalculator()
        result = calculator.calculate(input_data)

        assert "month" in result.data.columns, (
            "WindRoseCalculator output must include 'month' column"
        )

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
            air_density=1.225,
        )

        calculator = WindRoseCalculator()
        result = calculator.calculate(input_data)

        assert "month_name" in result.data.columns, (
            "WindRoseCalculator output must include 'month_name' column"
        )

    def test_calculator_produces_all_8_columns(self) -> None:
        """Verify calculator produces all 8 columns matching CorrectWindRoseSchema."""
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
            air_density=1.225,
        )

        calculator = WindRoseCalculator()
        result = calculator.calculate(input_data)

        expected_columns = {
            "month",
            "month_name",
            "sector",
            "sector_name",
            "height",
            "interpolation_marker",
            "frequency",
            "wind_power_density",
        }

        actual_columns = set(result.data.columns)

        assert actual_columns == expected_columns, (
            f"Expected columns: {expected_columns}, but got: {actual_columns}"
        )

    def test_calculator_data_matches_correct_schema(self) -> None:
        """Verify calculator output validates against CorrectWindRoseSchema."""
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
            air_density=1.225,
        )

        calculator = WindRoseCalculator()
        result = calculator.calculate(input_data)

        # The result should validate against the correct schema
        assert result.schema == CorrectWindRoseSchema, (
            f"Result schema should be CorrectWindRoseSchema (8 columns), "
            f"but got schema with columns: {set(result.data.columns)}"
        )
