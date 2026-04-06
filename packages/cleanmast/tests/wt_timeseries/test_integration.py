"""Integration tests for wt_timeseries module."""

import json
from datetime import datetime

import numpy as np
import polars as pl
import pyarrow.parquet as pq
import pytest
from cleanmast.application.usecases.generate_wt_timeseries import generate_wt_timeseries
from cleanmast.application.usecases.recommend_wt_timeseries import recommend_wt_timeseries
from cleanmast.subdomains.configuration import load_wt_timeseries_config
from cleanmast.subdomains.dataingestion.value_objects import SensorColumn
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)
from cleanmast.subdomains.dataprocessing.services import (
    process_single_mast_csv,
    process_turbulence_for_mast,
)


class TestFullWorkflow:
    """Integration tests for full workflow: recommend -> execute."""

    def create_parquet_with_sensors(self, parquet_path, sensors, data):
        """Helper to create a parquet file with embedded sensor metadata."""
        # Handle timestamp column properly
        if "timestamp" in data:
            timestamps = data["timestamp"]
            if isinstance(timestamps, list) and len(timestamps) > 0:
                # If it's already a Series, keep it
                if isinstance(timestamps, pl.Series):
                    pass  # Already a Series
                else:
                    # Ensure all timestamps are Python datetime objects
                    converted = []
                    for ts in timestamps:
                        if isinstance(ts, datetime):
                            converted.append(ts)
                        else:
                            # Convert pl.datetime() expressions
                            converted.append(ts)
                    data = dict(data)  # Make a copy
                    data["timestamp"] = pl.Series("timestamp", converted, dtype=pl.Datetime)

        df = pl.DataFrame(data)

        # Ensure timestamp column is datetime type
        if "timestamp" in df.columns and df["timestamp"].dtype != pl.Datetime:
            df = df.with_columns(pl.col("timestamp").cast(pl.Datetime))

        table = df.to_arrow()

        # Serialize sensors to JSON
        sensors_list = [
            {
                "columnName": s.column_name,
                "sensorType": s.sensor_type,
                "sensorDirection": s.sensor_direction,
                "height": s.height,
                "statType": s.stat_type,
                "unit": s.unit,
            }
            for s in sensors
        ]
        sensors_json = json.dumps({"sensors": sensors_list})

        writer = pq.ParquetWriter(parquet_path, table.schema)
        writer.add_key_value_metadata({"cleanmast_sensors": sensors_json})
        writer.write_table(table)
        writer.close()

    def test_recommend_command_creates_config(self, tmp_path):
        """Test that recommend command creates valid configuration."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        # Create fill-heights output directory
        fill_heights_dir = project_dir / "representative-year-fill-heights"
        fill_heights_dir.mkdir(parents=True)

        # Create fill-heights-representative-year.toml config
        import tomli_w
        from cleanmast.subdomains.configuration import (
            FillHeightsConfiguration,
            MastFillConfig,
        )
        from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
            TimeSeriesSource,
        )

        fill_heights_config = FillHeightsConfiguration(
            strategy="default",
            masts=[
                MastFillConfig(
                    name="TGL1",
                    input=TimeSeriesSource(data="./representative-year/TGL1.parquet"),
                    output=TimeSeriesSource(data="./representative-year-fill-heights/TGL1.parquet"),
                    windspeed=[],
                    winddirection=[],
                ),
            ],
        )

        fill_heights_toml = project_dir / "fill-heights-representative-year.toml"
        with open(fill_heights_toml, "wb") as f:
            tomli_w.dump(fill_heights_config.model_dump(exclude_none=True), f)

        # Create sample parquet with sensors at multiple heights
        sensors = [
            # WindSpeed sensors at heights >= 100m
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WS_120m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=120.0,
                stat_type="avg",
                unit="m/s",
            ),
            # WindSpeed sensors at heights < 100m (should not be in csv_heights)
            SensorColumn(
                column_name="WS_80m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
            # WindSpeed SD sensors (for turbulence)
            SensorColumn(
                column_name="WS_100m_sd",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=100.0,
                stat_type="sd",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WS_80m_sd",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=80.0,
                stat_type="sd",
                unit="m/s",
            ),
            # WindDirection sensors
            SensorColumn(
                column_name="WD_100m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="deg",
            ),
            SensorColumn(
                column_name="WD_120m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=120.0,
                stat_type="avg",
                unit="deg",
            ),
            SensorColumn(
                column_name="WD_80m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

        np.random.seed(42)
        data = {
            "timestamp": pl.datetime_range(
                start=pl.datetime(2023, 1, 1, 0, 0),
                end=pl.datetime(2023, 1, 2, 0, 0),
                interval="10m",
                eager=True,
            ),
            "WS_100m_avg": np.random.uniform(5, 15, 145),
            "WS_120m_avg": np.random.uniform(5, 15, 145),
            "WS_80m_avg": np.random.uniform(5, 15, 145),
            "WS_100m_sd": np.random.uniform(0.5, 2, 145),
            "WS_80m_sd": np.random.uniform(0.5, 2, 145),
            "WD_100m_avg": np.random.uniform(0, 360, 145),
            "WD_120m_avg": np.random.uniform(0, 360, 145),
            "WD_80m_avg": np.random.uniform(0, 360, 145),
        }

        self.create_parquet_with_sensors(
            fill_heights_dir / "TGL1.parquet", sensors, data
        )

        # Run recommend command
        config_path = recommend_wt_timeseries(project_dir)

        # Verify config was created
        assert config_path.exists()

        # Load and verify config
        config = load_wt_timeseries_config(config_path)
        assert len(config.masts) == 1
        assert config.masts[0].name == "TGL1"

        # Verify csv_heights only includes heights >= 100m with both WS and WD
        assert 100.0 in config.masts[0].csv_heights
        assert 120.0 in config.masts[0].csv_heights
        assert 80.0 not in config.masts[0].csv_heights  # < 100m

        # Verify turbulence heights includes heights with WS avg + SD
        assert 100.0 in config.masts[0].turbulence_heights
        assert 80.0 in config.masts[0].turbulence_heights

    def test_execute_command_processes_masts(self, tmp_path):
        """Test that execute command processes all configured masts."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        # Create fill-heights output directory
        fill_heights_dir = project_dir / "representative-year-fill-heights"
        fill_heights_dir.mkdir(parents=True)

        # Create fill-heights-representative-year.toml config
        import tomli_w
        from cleanmast.subdomains.configuration import (
            FillHeightsConfiguration,
            MastFillConfig,
        )
        from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
            TimeSeriesSource,
        )

        fill_heights_config = FillHeightsConfiguration(
            strategy="default",
            masts=[
                MastFillConfig(
                    name="TGL1",
                    input=TimeSeriesSource(data="./representative-year/TGL1.parquet"),
                    output=TimeSeriesSource(data="./representative-year-fill-heights/TGL1.parquet"),
                    windspeed=[],
                    winddirection=[],
                ),
                MastFillConfig(
                    name="TGL2",
                    input=TimeSeriesSource(data="./representative-year/TGL2.parquet"),
                    output=TimeSeriesSource(data="./representative-year-fill-heights/TGL2.parquet"),
                    windspeed=[],
                    winddirection=[],
                ),
            ],
        )

        fill_heights_toml = project_dir / "fill-heights-representative-year.toml"
        with open(fill_heights_toml, "wb") as f:
            tomli_w.dump(fill_heights_config.model_dump(exclude_none=True), f)

        # Create two masts
        for mast_name in ["TGL1", "TGL2"]:
            sensors = [
                SensorColumn(
                    column_name="WS_100m_avg",
                    sensor_type="WindSpeed",
                    sensor_direction="N",
                    height=100.0,
                    stat_type="avg",
                    unit="m/s",
                ),
                SensorColumn(
                    column_name="WD_100m_avg",
                    sensor_type="WindDirection",
                    sensor_direction="N",
                    height=100.0,
                    stat_type="avg",
                    unit="deg",
                ),
            ]

            data = {
                "timestamp": pl.Series("timestamp", [datetime(2023, 1, 1, 0, 0, 0)], dtype=pl.Datetime),
                "WS_100m_avg": [10.0],
                "WD_100m_avg": [180.0],
            }

            self.create_parquet_with_sensors(
                fill_heights_dir / f"{mast_name}.parquet", sensors, data
            )

        # Create config
        config_path = recommend_wt_timeseries(project_dir)

        # Execute
        generate_wt_timeseries(config_path)

        # Verify outputs
        output_dir = project_dir / "wt-timeseries"
        assert (output_dir / "TGL1.csv").exists()
        assert (output_dir / "TGL2.csv").exists()

        # Verify CSV content
        df1 = pl.read_csv(output_dir / "TGL1.csv")
        assert "timestamp" in df1.columns
        assert "WS_100m_avg" in df1.columns
        assert "WD_100m_avg" in df1.columns


class TestHeightFiltering:
    """Tests for height filtering behavior."""

    def test_csv_heights_filtered_below_100m(self, tmp_path):
        """Test that CSV output filters heights < 100m."""
        from cleanmast.subdomains.configuration import WtTimeSeriesMast

        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        filled_dir = project_dir / "representative-year" / "filled"
        filled_dir.mkdir(parents=True)

        sensors = [
            SensorColumn(
                column_name="WS_80m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_80m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="deg",
            ),
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_100m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

        data = {
            "timestamp": pl.Series("timestamp", [datetime(2023, 1, 1, 0, 0, 0)], dtype=pl.Datetime),
            "WS_80m_avg": [8.0],
            "WD_80m_avg": [180.0],
            "WS_100m_avg": [10.0],
            "WD_100m_avg": [185.0],
        }

        df = pl.DataFrame(data)
        table = df.to_arrow()

        sensors_list = [
            {
                "columnName": s.column_name,
                "sensorType": s.sensor_type,
                "sensorDirection": s.sensor_direction,
                "height": s.height,
                "statType": s.stat_type,
                "unit": s.unit,
            }
            for s in sensors
        ]
        sensors_json = json.dumps({"sensors": sensors_list})

        parquet_path = filled_dir / "TGL1.parquet"
        writer = pq.ParquetWriter(parquet_path, table.schema)
        writer.add_key_value_metadata({"cleanmast_sensors": sensors_json})
        writer.write_table(table)
        writer.close()

        # Config with heights both >= 100m and < 100m
        # csv_heights must be >= 100m per validation
        from pydantic import ValidationError

        # 80m should fail validation (csv_heights must be >= 100)
        with pytest.raises(ValidationError) as exc_info:
            WtTimeSeriesMast(
                name="TGL1",
                input=TimeSeriesSource(data="./representative-year/filled/TGL1.parquet"),
                csv_heights=[80.0, 100.0],  # 80m < 100m, should fail validation
                turbulence_heights=[],
            )

        assert "csv_heights must be >= 100.0" in str(exc_info.value)

    def test_turbulence_any_height_allowed(self, tmp_path):
        """Test that turbulence can be calculated at any height."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        filled_dir = project_dir / "representative-year" / "filled"
        filled_dir.mkdir(parents=True)

        sensors = [
            SensorColumn(
                column_name="WS_80m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WS_80m_sd",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=80.0,
                stat_type="sd",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_80m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

        np.random.seed(42)
        n = 100
        timestamps = pl.datetime_range(
            start=pl.datetime(2023, 1, 1, 0, 0),
            end=pl.datetime(2023, 1, 1, 16, 30),
            interval="10m",
            eager=True,
        )[:n]

        data = {
            "timestamp": timestamps,
            "WS_80m_avg": np.random.uniform(5, 15, n),
            "WS_80m_sd": np.random.uniform(0.5, 2, n),
            "WD_80m_avg": np.random.uniform(0, 360, n),
        }

        df = pl.DataFrame(data)

        # Ensure timestamp is datetime type
        if df["timestamp"].dtype != pl.Datetime:
            df = df.with_columns(pl.col("timestamp").cast(pl.Datetime))

        table = df.to_arrow()

        sensors_list = [
            {
                "columnName": s.column_name,
                "sensorType": s.sensor_type,
                "sensorDirection": s.sensor_direction,
                "height": s.height,
                "statType": s.stat_type,
                "unit": s.unit,
            }
            for s in sensors
        ]
        sensors_json = json.dumps({"sensors": sensors_list})

        parquet_path = filled_dir / "TGL1.parquet"
        writer = pq.ParquetWriter(parquet_path, table.schema)
        writer.add_key_value_metadata({"cleanmast_sensors": sensors_json})
        writer.write_table(table)
        writer.close()

        from cleanmast.subdomains.configuration import WtTimeSeriesMast

        mast = WtTimeSeriesMast(
            name="TGL1",
            input=TimeSeriesSource(data="./representative-year/filled/TGL1.parquet"),
            csv_heights=[100.0],  # This won't work, but turbulence should
            turbulence_heights=[80.0],  # 80m is valid for turbulence
        )

        # Process turbulence (should work at 80m)
        process_turbulence_for_mast(mast, project_dir)

        # Verify turbulence file was created
        turbulence_file = project_dir / "wt-timeseries" / "turbulence-TGL1" / "meteodyn_ti_80m.txt"
        assert turbulence_file.exists()


class TestPathResolution:
    """Tests for path resolution in configuration."""

    def test_relative_paths_resolved(self, tmp_path):
        """Test that relative paths are resolved relative to config file."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        filled_dir = project_dir / "representative-year" / "filled"
        filled_dir.mkdir(parents=True)

        # Create minimal parquet
        sensors = [
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_100m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

        # Create data with proper timestamp type
        data = {
            "timestamp": pl.Series("timestamp", [datetime(2023, 1, 1, 0, 0, 0)], dtype=pl.Datetime),
            "WS_100m_avg": [10.0],
            "WD_100m_avg": [180.0],
        }

        df = pl.DataFrame(data)
        table = df.to_arrow()

        sensors_list = [
            {
                "columnName": s.column_name,
                "sensorType": s.sensor_type,
                "sensorDirection": s.sensor_direction,
                "height": s.height,
                "statType": s.stat_type,
                "unit": s.unit,
            }
            for s in sensors
        ]
        sensors_json = json.dumps({"sensors": sensors_list})

        parquet_path = filled_dir / "TGL1.parquet"
        writer = pq.ParquetWriter(parquet_path, table.schema)
        writer.add_key_value_metadata({"cleanmast_sensors": sensors_json})
        writer.write_table(table)
        writer.close()

        # Create config file with relative path
        config_file = project_dir / "wt-timeseries.toml"
        config_file.write_text("""
[[masts]]
name = "TGL1"
input.data = "./representative-year/filled/TGL1.parquet"
csv_heights = [100.0]
turbulence_heights = []
""")

        # Load config
        config = load_wt_timeseries_config(config_file)

        # Path should be resolved to absolute
        expected_path = (project_dir / "representative-year" / "filled" / "TGL1.parquet").resolve()
        assert config.masts[0].input.data == str(expected_path)

        # Should be able to process with resolved path
        process_single_mast_csv(config.masts[0], project_dir)

        # Verify output
        assert (project_dir / "wt-timeseries" / "TGL1.csv").exists()


class TestErrorHandling:
    """Tests for error handling in integration scenarios."""

    def test_missing_input_file(self, tmp_path):
        """Test handling of missing input file."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        from cleanmast.subdomains.configuration import WtTimeSeriesMast

        mast = WtTimeSeriesMast(
            name="TGL1",
            input=TimeSeriesSource(data="./representative-year/filled/nonexistent.parquet"),
            csv_heights=[100.0],
            turbulence_heights=[],
        )

        with pytest.raises(FileNotFoundError):
            process_single_mast_csv(mast, project_dir)

    def test_missing_representative_year_directory(self, tmp_path):
        """Test handling of missing representative-year directory."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        with pytest.raises(FileNotFoundError) as exc_info:
            recommend_wt_timeseries(project_dir)

        assert "representative-year" in str(exc_info.value).lower()

    def test_no_parquet_files(self, tmp_path):
        """Test handling when no parquet files exist."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        filled_dir = project_dir / "representative-year" / "filled"
        filled_dir.mkdir(parents=True)

        with pytest.raises(FileNotFoundError) as exc_info:
            recommend_wt_timeseries(project_dir)

        assert "no parquet files" in str(exc_info.value).lower() or "parquet" in str(exc_info.value).lower()
