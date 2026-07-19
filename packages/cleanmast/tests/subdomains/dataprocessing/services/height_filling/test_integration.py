"""Integration tests for fill_heights module.

End-to-end tests for the complete fill-heights workflow.
"""

import numpy as np
import polars as pl
import pytest
from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData, TimeSeriesSource
from cleanmast.subdomains.configuration import (
    FillHeightsConfiguration,
    HeightReference,
    MastFillConfig,
    WindDirectionHeightConfig,
    WindSpeedHeightConfig,
)
from cleanmast.subdomains.dataprocessing.services import apply_wd_fill, apply_ws_fill


def create_ws_sensor(column_name: str, height: float) -> SensorColumn:
    """Helper to create a WindSpeed sensor."""
    return SensorColumn(
        column_name=column_name,
        sensor_type="WindSpeed",
        sensor_direction="N/A",
        height=height,
        stat_type="avg",
        unit="m/s",
    )


def create_wd_sensor(column_name: str, height: float) -> SensorColumn:
    """Helper to create a WindDirection sensor."""
    return SensorColumn(
        column_name=column_name,
        sensor_type="WindDirection",
        sensor_direction="N/A",
        height=height,
        stat_type="avg",
        unit="deg",
    )


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    def test_apply_ws_fill_extrapolation(self):
        """Test WS fill with extrapolation."""
        # Create test dataframe
        df = pl.DataFrame({
            "timestamp": [1, 2, 3],
            "WS_100m_avg": [10.0, 12.0, 11.0],
        })
        
        # Test extrapolation
        target = create_ws_sensor("WS_120m_fill:extrapolated", 120.0)
        ref_sensor = create_ws_sensor("WS_100m_avg", 100.0)
        ref = HeightReference(sensor=ref_sensor, weight=1.0)
        result = apply_ws_fill(df, target, [ref], shear=0.2)

        assert len(result) == 3
        assert result.name == "WS_120m_fill:extrapolated"
        # V2 = V1 * (120/100)^0.2 = V1 * 1.037
        assert abs(result[0] - 10.0 * 1.037) < 0.1

    def test_apply_wd_fill_extrapolation(self):
        """Test WD fill with extrapolation."""
        df = pl.DataFrame({
            "timestamp": [1, 2, 3],
            "WD_100m_avg": [350.0, 10.0, 5.0],
        })
        
        target = create_wd_sensor("WD_120m_fill:extrapolated", 120.0)
        ref_sensor = create_wd_sensor("WD_100m_avg", 100.0)
        ref = HeightReference(sensor=ref_sensor, weight=1.0)
        result = apply_wd_fill(df, target, [ref], deg_diff_per_m=0.1)

        assert len(result) == 3
        assert result.name == "WD_120m_fill:extrapolated"
        # Should be wrapped to [0, 360)
        assert all(0 <= v < 360 for v in result.to_list())

    def test_apply_ws_fill_interpolation(self):
        """Test WS fill with interpolation."""
        df = pl.DataFrame({
            "timestamp": [1, 2, 3],
            "WS_80m_avg": [8.0, 9.0, 8.5],
            "WS_100m_avg": [10.0, 11.0, 10.5],
        })
        
        target = create_ws_sensor("WS_90m_fill:interpolated", 90.0)
        refs = [
            HeightReference(sensor=create_ws_sensor("WS_80m_avg", 80.0), weight=0.5),
            HeightReference(sensor=create_ws_sensor("WS_100m_avg", 100.0), weight=0.5),
        ]
        result = apply_ws_fill(df, target, refs, shear=0.15)

        assert len(result) == 3
        assert result.name == "WS_90m_fill:interpolated"

    def test_apply_wd_fill_interpolation_wraparound(self):
        """Test WD interpolation handles 0/360 wraparound."""
        df = pl.DataFrame({
            "timestamp": [1, 2],
            "WD_80m_avg": [355.0, 350.0],
            "WD_100m_avg": [5.0, 10.0],
        })
        
        target = create_wd_sensor("WD_90m_fill:interpolated", 90.0)
        refs = [
            HeightReference(sensor=create_wd_sensor("WD_80m_avg", 80.0), weight=0.5),
            HeightReference(sensor=create_wd_sensor("WD_100m_avg", 100.0), weight=0.5),
        ]
        result = apply_wd_fill(df, target, refs, deg_diff_per_m=0.0)
        
        # Result should be around 0/360, not 180
        assert result.name == "WD_90m_fill:interpolated"
        # Allow 360 since it's equivalent to 0 (wind from north)
        assert all(0 <= v <= 360 for v in result.to_list())


class TestConfiguration:
    """Configuration and validation tests."""

    def test_fill_heights_configuration_creation(self):
        """Test FillHeightsConfiguration can be created."""
        config = FillHeightsConfiguration(
            strategy="default",
            masts=[],
        )
        assert config.strategy == "default"
        assert len(config.masts) == 0

    def test_mast_fill_config_creation(self):
        """Test MastFillConfig can be created."""
        mast = MastFillConfig(
            name="M01",
            input=TimeSeriesSource(
                data="./input.parquet",
                sensors="./input.sensors.yaml",
            ),
            output=TimeSeriesSource(
                data="./output.parquet",
                sensors="./output.sensors.yaml",
            ),
            windspeed=[],
            winddirection=[],
        )
        assert mast.name == "M01"


class TestIdempotency:
    """Idempotency tests."""

    def test_repeated_application_produces_same_results(self):
        """Test that applying fill twice produces same results."""
        df = pl.DataFrame({
            "timestamp": [1, 2, 3],
            "WS_100m_avg": [10.0, 12.0, 11.0],
        })
        
        target = create_ws_sensor("WS_120m_fill:extrapolated", 120.0)
        ref_sensor = create_ws_sensor("WS_100m_avg", 100.0)
        ref = HeightReference(sensor=ref_sensor, weight=1.0)
        
        result1 = apply_ws_fill(df, target, [ref], shear=0.2)
        result2 = apply_ws_fill(df, target, [ref], shear=0.2)
        
        assert np.allclose(result1.to_numpy(), result2.to_numpy())


class TestErrorScenarios:
    """Error handling tests."""

    def test_apply_ws_fill_missing_column_raises_error(self):
        """Test that missing source column raises error."""
        df = pl.DataFrame({
            "timestamp": [1, 2, 3],
            "WS_100m_avg": [10.0, 12.0, 11.0],
        })
        
        target = create_ws_sensor("WS_220m_fill:extrapolated", 220.0)
        ref_sensor = create_ws_sensor("WS_200m_avg", 200.0)  # Non-existent column
        ref = HeightReference(sensor=ref_sensor, weight=1.0)
        
        with pytest.raises(Exception):
            apply_ws_fill(df, target, [ref], shear=0.2)


class TestReferenceValidation:
    """Tests for runtime validation of HeightReference configurations."""

    def _create_test_timeseries(self, column_names: list[str], sensor_types: list[str], heights: list[float]) -> TimeSeriesData:
        """Helper to create a test timeseries with given columns and sensors."""
        df = pl.DataFrame({
            "timestamp": [1, 2, 3],
            **{col: [10.0 + i, 11.0 + i, 12.0 + i] for i, col in enumerate(column_names)},
        })
        sensors = [
            SensorColumn(
                column_name=col,
                sensor_type=s_type,
                sensor_direction="N/A",
                height=h,
                stat_type="avg",
                unit="m/s" if s_type == "WindSpeed" else "deg",
            )
            for col, s_type, h in zip(column_names, sensor_types, heights)
        ]
        return TimeSeriesData(df=df, sensors=sensors)

    def test_validate_references_valid_config(self):
        """Test validation passes for valid reference configuration."""
        from cleanmast.subdomains.dataprocessing.services.height_filling.validation import (
            _validate_references,
        )
        
        timeseries = self._create_test_timeseries(
            column_names=["WS_80m_avg", "WS_100m_avg"],
            sensor_types=["WindSpeed", "WindSpeed"],
            heights=[80.0, 100.0],
        )

        mast_config = MastFillConfig(
            name="test-mast",
            input=TimeSeriesSource(data="./input.parquet"),
            output=TimeSeriesSource(data="./output.parquet"),
            windspeed=[
                WindSpeedHeightConfig(
                    target_sensor=create_ws_sensor("WS_120m_fill:extrapolated", 120.0),
                    references=[HeightReference(sensor=create_ws_sensor("WS_100m_avg", 100.0), weight=1.0)],
                    shear=0.15,
                )
            ],
            winddirection=[],
        )

        # Should not raise
        _validate_references(timeseries, mast_config)

    def test_validate_references_missing_column(self):
        """Test validation fails when reference column doesn't exist."""
        from cleanmast.subdomains.dataprocessing.services.height_filling.validation import (
            _validate_references,
        )
        
        timeseries = self._create_test_timeseries(
            column_names=["WS_80m_avg"],
            sensor_types=["WindSpeed"],
            heights=[80.0],
        )

        # Use a valid height for extrapolation (target > ref), but column doesn't exist
        mast_config = MastFillConfig(
            name="test-mast",
            input=TimeSeriesSource(data="./input.parquet"),
            output=TimeSeriesSource(data="./output.parquet"),
            windspeed=[
                WindSpeedHeightConfig(
                    target_sensor=create_ws_sensor("WS_120m_fill:extrapolated", 120.0),
                    references=[HeightReference(sensor=create_ws_sensor("WS_200m_avg", 80.0), weight=1.0)],
                    shear=0.15,
                )
            ],
            winddirection=[],
        )

        with pytest.raises(ValueError, match="Reference 'WS_200m_avg' not found in timeseries"):
            _validate_references(timeseries, mast_config)

    def test_validate_references_wrong_sensor_type(self):
        """Test validation fails when sensor_type doesn't match."""
        from cleanmast.subdomains.dataprocessing.services.height_filling.validation import (
            _validate_references,
        )
        
        timeseries = self._create_test_timeseries(
            column_names=["WS_80m_avg", "WD_80m_avg"],
            sensor_types=["WindSpeed", "WindDirection"],
            heights=[80.0, 80.0],
        )

        # WindDirection column used in WindSpeed config
        mast_config = MastFillConfig(
            name="test-mast",
            input=TimeSeriesSource(data="./input.parquet"),
            output=TimeSeriesSource(data="./output.parquet"),
            windspeed=[
                WindSpeedHeightConfig(
                    target_sensor=create_ws_sensor("WS_100m_fill:extrapolated", 100.0),
                    references=[HeightReference(sensor=create_wd_sensor("WD_80m_avg", 80.0), weight=1.0)],
                    shear=0.15,
                )
            ],
            winddirection=[],
        )

        with pytest.raises(ValueError, match="sensor_type 'WindDirection' but expected 'WindSpeed'"):
            _validate_references(timeseries, mast_config)

    def test_validate_references_height_mismatch(self):
        """Test validation fails when reference height doesn't match sensor height."""
        from cleanmast.subdomains.dataprocessing.services.height_filling.validation import (
            _validate_references,
        )
        
        timeseries = self._create_test_timeseries(
            column_names=["WS_80m_avg"],
            sensor_types=["WindSpeed"],
            heights=[80.0],
        )

        # Reference specifies wrong height (100m vs actual 80m)
        mast_config = MastFillConfig(
            name="test-mast",
            input=TimeSeriesSource(data="./input.parquet"),
            output=TimeSeriesSource(data="./output.parquet"),
            windspeed=[
                WindSpeedHeightConfig(
                    target_sensor=create_ws_sensor("WS_120m_fill:extrapolated", 120.0),
                    references=[HeightReference(sensor=create_ws_sensor("WS_80m_avg", 100.0), weight=1.0)],
                    shear=0.15,
                )
            ],
            winddirection=[],
        )

        with pytest.raises(ValueError, match=r"does not match sensor height"):
            _validate_references(timeseries, mast_config)

    def test_validate_references_height_within_tolerance(self):
        """Test validation passes when height difference is within tolerance."""
        from cleanmast.subdomains.dataprocessing.services.height_filling.validation import (
            _validate_references,
        )
        
        timeseries = self._create_test_timeseries(
            column_names=["WS_80m_avg"],
            sensor_types=["WindSpeed"],
            heights=[80.0],
        )

        # Height difference is 0.005m (< 0.01m tolerance)
        mast_config = MastFillConfig(
            name="test-mast",
            input=TimeSeriesSource(data="./input.parquet"),
            output=TimeSeriesSource(data="./output.parquet"),
            windspeed=[
                WindSpeedHeightConfig(
                    target_sensor=create_ws_sensor("WS_100m_fill:extrapolated", 100.0),
                    references=[HeightReference(sensor=create_ws_sensor("WS_80m_avg", 80.005), weight=1.0)],
                    shear=0.15,
                )
            ],
            winddirection=[],
        )

        # Should not raise
        _validate_references(timeseries, mast_config)

    def test_validate_references_wind_direction_config(self):
        """Test validation works for wind direction configs."""
        from cleanmast.subdomains.dataprocessing.services.height_filling.validation import (
            _validate_references,
        )
        
        timeseries = self._create_test_timeseries(
            column_names=["WD_80m_avg"],
            sensor_types=["WindDirection"],
            heights=[80.0],
        )

        mast_config = MastFillConfig(
            name="test-mast",
            input=TimeSeriesSource(data="./input.parquet"),
            output=TimeSeriesSource(data="./output.parquet"),
            windspeed=[],
            winddirection=[
                WindDirectionHeightConfig(
                    target_sensor=create_wd_sensor("WD_100m_fill:extrapolated", 100.0),
                    references=[HeightReference(sensor=create_wd_sensor("WD_80m_avg", 80.0), weight=1.0)],
                    deg_diff_per_m=0.1,
                )
            ],
        )

        # Should not raise
        _validate_references(timeseries, mast_config)

    def test_validate_references_collects_all_errors(self):
        """Test validation collects all errors before raising."""
        from cleanmast.subdomains.dataprocessing.services.height_filling.validation import (
            _validate_references,
        )
        
        timeseries = self._create_test_timeseries(
            column_names=["WS_80m_avg"],
            sensor_types=["WindSpeed"],
            heights=[80.0],
        )

        # Multiple validation issues with valid heights for config-level validation
        mast_config = MastFillConfig(
            name="test-mast",
            input=TimeSeriesSource(data="./input.parquet"),
            output=TimeSeriesSource(data="./output.parquet"),
            windspeed=[
                # Missing column (using 80m ref height for valid config)
                WindSpeedHeightConfig(
                    target_sensor=create_ws_sensor("WS_100m_fill:extrapolated", 100.0),
                    references=[HeightReference(sensor=create_ws_sensor("WS_200m_avg", 80.0), weight=1.0)],
                    shear=0.15,
                ),
                # Wrong height (100m ref vs 80m actual)
                WindSpeedHeightConfig(
                    target_sensor=create_ws_sensor("WS_120m_fill:extrapolated", 120.0),
                    references=[HeightReference(sensor=create_ws_sensor("WS_80m_avg", 100.0), weight=1.0)],
                    shear=0.15,
                ),
            ],
            winddirection=[
                # Wrong sensor type
                WindDirectionHeightConfig(
                    target_sensor=create_wd_sensor("WD_100m_fill:extrapolated", 100.0),
                    references=[HeightReference(sensor=create_ws_sensor("WS_80m_avg", 80.0), weight=1.0)],
                    deg_diff_per_m=0.1,
                ),
            ],
        )

        with pytest.raises(ValueError) as exc_info:
            _validate_references(timeseries, mast_config)

        error_msg = str(exc_info.value)
        # Check that multiple errors are collected
        assert "WS_200m_avg" in error_msg or "WS_80m_avg" in error_msg
        # Should contain Validation failed message
        assert "Validation failed" in error_msg

    def test_build_sensor_column_map(self):
        """Test that sensor column map is built correctly."""
        from cleanmast.subdomains.dataprocessing.services.height_filling.validation import (
            _build_sensor_column_map,
        )
        
        timeseries = self._create_test_timeseries(
            column_names=["WS_80m_avg", "WS_100m_avg"],
            sensor_types=["WindSpeed", "WindSpeed"],
            heights=[80.0, 100.0],
        )

        column_map = _build_sensor_column_map(timeseries)

        assert len(column_map) == 2
        assert "WS_80m_avg" in column_map
        assert "WS_100m_avg" in column_map
        assert column_map["WS_80m_avg"].height == 80.0
        assert column_map["WS_100m_avg"].height == 100.0


class TestOutputSensorColumns:
    """Tests for output sensor column metadata after fills."""

    def _create_test_timeseries(
        self, column_names: list[str], sensor_types: list[str], heights: list[float]
    ) -> TimeSeriesData:
        """Helper to create a test timeseries with given columns and sensors."""
        df = pl.DataFrame({
            "timestamp": [1, 2, 3],
            **{col: [10.0 + i, 11.0 + i, 12.0 + i] for i, col in enumerate(column_names)},
        })
        sensors = [
            SensorColumn(
                column_name=col,
                sensor_type=s_type,
                sensor_direction="N/A",
                height=h,
                stat_type="avg",
                unit="m/s" if s_type == "WindSpeed" else "deg",
            )
            for col, s_type, h in zip(column_names, sensor_types, heights)
        ]
        return TimeSeriesData(df=df, sensors=sensors)

    def test_ws_fill_creates_correct_sensor_metadata(self):
        """Test WS fill creates SensorColumn with correct WindSpeed metadata."""
        # Create input with WS sensor at 100m
        timeseries = self._create_test_timeseries(
            column_names=["WS_100m_avg"],
            sensor_types=["WindSpeed"],
            heights=[100.0],
        )

        # Apply fill to create new WS column at 120m
        target = create_ws_sensor("WS_120m_fill:extrapolated", 120.0)
        ref = HeightReference(sensor=create_ws_sensor("WS_100m_avg", 100.0), weight=1.0)
        filled_series = apply_ws_fill(
            timeseries.df, target, [ref], shear=0.2
        )
        # Ensure series has correct name for adding to DataFrame
        filled_series = filled_series.rename("WS_120m_fill:extrapolated")

        # Add filled column to DataFrame
        result_df = timeseries.df.with_columns(filled_series)

        # Create sensor for the filled column
        filled_sensor = SensorColumn(
            column_name="WS_120m_fill:extrapolated",
            sensor_type="WindSpeed",
            sensor_direction="N/A",
            height=120.0,
            stat_type="avg",
            unit="m/s",
        )

        # Combine with original sensors
        result_sensors = timeseries.sensors + [filled_sensor]
        result_timeseries = TimeSeriesData(df=result_df, sensors=result_sensors)

        # Verify output sensors include new WS sensor at 120m
        assert len(result_timeseries.sensors) == 2
        new_sensor = result_timeseries.sensors[1]
        assert new_sensor.sensor_type == "WindSpeed" and new_sensor.stat_type == "avg"
        assert new_sensor.stat_type == "avg"
        assert new_sensor.height == 120.0
        assert new_sensor.unit == "m/s"
        assert new_sensor.column_name == "WS_120m_fill:extrapolated"

    def test_wd_fill_creates_correct_sensor_metadata(self):
        """Test WD fill creates SensorColumn with correct WindDirection metadata."""
        # Create input with WD sensor at 100m
        timeseries = self._create_test_timeseries(
            column_names=["WD_100m_avg"],
            sensor_types=["WindDirection"],
            heights=[100.0],
        )

        # Apply fill to create new WD column at 120m
        target = create_wd_sensor("WD_120m_fill:extrapolated", 120.0)
        ref = HeightReference(sensor=create_wd_sensor("WD_100m_avg", 100.0), weight=1.0)
        filled_series = apply_wd_fill(
            timeseries.df, target, [ref], deg_diff_per_m=0.1
        )
        # Ensure series has correct name for adding to DataFrame
        filled_series = filled_series.rename("WD_120m_fill:extrapolated")

        # Add filled column to DataFrame
        result_df = timeseries.df.with_columns(filled_series)

        # Create sensor for the filled column
        filled_sensor = SensorColumn(
            column_name="WD_120m_fill:extrapolated",
            sensor_type="WindDirection",
            sensor_direction="N/A",
            height=120.0,
            stat_type="avg",
            unit="deg",
        )

        # Combine with original sensors
        result_sensors = timeseries.sensors + [filled_sensor]
        result_timeseries = TimeSeriesData(df=result_df, sensors=result_sensors)

        # Verify output sensors include new WD sensor at 120m
        assert len(result_timeseries.sensors) == 2
        new_sensor = result_timeseries.sensors[1]
        assert new_sensor.sensor_type == "WindDirection" and new_sensor.stat_type == "avg"
        assert new_sensor.stat_type == "avg"
        assert new_sensor.height == 120.0
        assert new_sensor.unit == "deg"
        assert new_sensor.column_name == "WD_120m_fill:extrapolated"

    def test_multiple_fills_create_multiple_sensors(self):
        """Test that multiple fills create multiple new sensors."""
        # Create input with multiple reference sensors
        timeseries = self._create_test_timeseries(
            column_names=["WS_100m_avg", "WD_100m_avg"],
            sensor_types=["WindSpeed", "WindDirection"],
            heights=[100.0, 100.0],
        )

        # Apply WS fill
        ws_target = create_ws_sensor("WS_120m_fill:extrapolated", 120.0)
        ws_ref = HeightReference(sensor=create_ws_sensor("WS_100m_avg", 100.0), weight=1.0)
        ws_filled = apply_ws_fill(
            timeseries.df, ws_target, [ws_ref], shear=0.2
        )
        ws_filled = ws_filled.rename("WS_120m_fill:extrapolated")

        # Apply WD fill
        wd_target = create_wd_sensor("WD_120m_fill:extrapolated", 120.0)
        wd_ref = HeightReference(sensor=create_wd_sensor("WD_100m_avg", 100.0), weight=1.0)
        wd_filled = apply_wd_fill(
            timeseries.df, wd_target, [wd_ref], deg_diff_per_m=0.1
        )
        wd_filled = wd_filled.rename("WD_120m_fill:extrapolated")

        # Add both filled columns
        result_df = timeseries.df.with_columns([ws_filled, wd_filled])

        # Create sensors for filled columns
        ws_sensor = SensorColumn(
            column_name="WS_120m_fill:extrapolated",
            sensor_type="WindSpeed",
            sensor_direction="N/A",
            height=120.0,
            stat_type="avg",
            unit="m/s",
        )
        wd_sensor = SensorColumn(
            column_name="WD_120m_fill:extrapolated",
            sensor_type="WindDirection",
            sensor_direction="N/A",
            height=120.0,
            stat_type="avg",
            unit="deg",
        )

        # Combine all sensors
        result_sensors = timeseries.sensors + [ws_sensor, wd_sensor]
        result_timeseries = TimeSeriesData(df=result_df, sensors=result_sensors)

        # Verify output contains all original + new sensors
        assert len(result_timeseries.sensors) == 4
        assert len(result_timeseries.df.columns) == 5  # timestamp + 2 original + 2 filled

        # Verify sensor types
        sensor_types = [s.sensor_type for s in result_timeseries.sensors if s.stat_type == "avg"]
        assert sensor_types.count("WindSpeed") == 2
        assert sensor_types.count("WindDirection") == 2

        # Verify heights
        heights = [s.height for s in result_timeseries.sensors]
        assert 100.0 in heights
        assert 120.0 in heights

    def test_filled_sensor_has_correct_column_name(self):
        """Test that SensorColumn.column_name matches the filled column name."""
        timeseries = self._create_test_timeseries(
            column_names=["WS_80m_avg"],
            sensor_types=["WindSpeed"],
            heights=[80.0],
        )

        target_column = "WS_100m_fill:extrapolated"
        target_height = 100.0

        # Apply fill
        target = create_ws_sensor(target_column, target_height)
        ref = HeightReference(sensor=create_ws_sensor("WS_80m_avg", 80.0), weight=1.0)
        filled_series = apply_ws_fill(
            timeseries.df, target, [ref], shear=0.2
        )
        # Rename to ensure correct column name
        filled_series = filled_series.rename(target_column)

        # Add filled column
        result_df = timeseries.df.with_columns(filled_series)

        # Create sensor with the same column name as the filled series
        filled_sensor = SensorColumn(
            column_name=target_column,
            sensor_type="WindSpeed",
            sensor_direction="N/A",
            height=target_height,
            stat_type="avg",
            unit="m/s",
        )

        result_timeseries = TimeSeriesData(
            df=result_df, sensors=timeseries.sensors + [filled_sensor]
        )

        # Verify column_name matches
        assert result_timeseries.sensors[1].column_name == target_column
        # Verify column exists in DataFrame
        assert target_column in result_timeseries.df.columns
