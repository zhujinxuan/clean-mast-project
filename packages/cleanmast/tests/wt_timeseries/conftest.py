"""Test fixtures for wt_timeseries module."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from cleanmast.subdomains.dataingestion.value_objects import SensorColumn
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import TimeSeriesSource
from cleanmast.subdomains.configuration import WtTimeSeriesMast


@pytest.fixture
def sample_turbulence_matrix():
    """Generate a reasonable randomized turbulence matrix."""
    np.random.seed(42)
    # 28 wind speed bins, 16 sectors, TI values 0.05-0.35
    matrix = np.random.uniform(0.05, 0.35, size=(28, 16))
    return matrix


@pytest.fixture
def synthetic_wind_timeseries():
    """Generate synthetic wind speed time series with turbulence.

    Creates a 1-year dataset with:
    - Weibull distribution for wind speed
    - Generated SD from target TI
    - Consistent wind direction
    """
    np.random.seed(42)
    n_samples = 365 * 24 * 6  # 1 year of 10-minute data

    # Weibull distribution parameters (typical for wind)
    scale = 8.0  # m/s
    shape = 2.0

    # Generate wind speeds
    wind_speeds = scale * np.random.weibull(shape, n_samples)
    wind_speeds = np.clip(wind_speeds, 0, 50)

    # Target TI (turbulence intensity)
    target_ti = 0.15

    # Generate SD from target TI
    wind_speed_sd = wind_speeds * target_ti + np.random.normal(0, 0.2, n_samples)
    wind_speed_sd = np.clip(wind_speed_sd, 0.1, None)

    # Wind direction (dominant from south with some spread)
    wind_directions = 180 + np.random.normal(0, 30, n_samples)
    wind_directions = wind_directions % 360

    # Timestamps
    start_time = datetime(2023, 1, 1, 0, 0)
    timestamps = [start_time + timedelta(minutes=10 * i) for i in range(n_samples)]

    df = pl.DataFrame({
        "timestamp": timestamps,
        "wind_speed_80m": wind_speeds,
        "wind_speed_sd_80m": wind_speed_sd,
        "wind_dir_80m": wind_directions,
    })

    return df, target_ti


@pytest.fixture
def test_project_structure(tmp_path):
    """Create a complete test project structure."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    # Create representative-year/filled directory
    filled_dir = project_dir / "representative-year" / "filled"
    filled_dir.mkdir(parents=True)

    # Create output directory
    output_dir = project_dir / "wt-timeseries"
    output_dir.mkdir(exist_ok=True)

    return project_dir, filled_dir, output_dir


@pytest.fixture
def sample_sensor_columns_with_sd():
    """Create sample sensor columns including WindSpeed SD."""
    return [
        # WindSpeed sensors at different heights
        SensorColumn(
            column_name="WS_80m_avg",
            sensor_type="WindSpeed",
            sensor_direction="N",
            height=80.0,
            stat_type="avg",
            unit="m/s",
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
            column_name="WS_120m_avg",
            sensor_type="WindSpeed",
            sensor_direction="N",
            height=120.0,
            stat_type="avg",
            unit="m/s",
        ),
        SensorColumn(
            column_name="WS_140m_avg",
            sensor_type="WindSpeed",
            sensor_direction="N",
            height=140.0,
            stat_type="avg",
            unit="m/s",
        ),
        # WindSpeed SD sensors
        SensorColumn(
            column_name="WS_80m_sd",
            sensor_type="WindSpeed",
            sensor_direction="N",
            height=80.0,
            stat_type="sd",
            unit="m/s",
        ),
        SensorColumn(
            column_name="WS_100m_sd",
            sensor_type="WindSpeed",
            sensor_direction="N",
            height=100.0,
            stat_type="sd",
            unit="m/s",
        ),
        SensorColumn(
            column_name="WS_120m_sd",
            sensor_type="WindSpeed",
            sensor_direction="N",
            height=120.0,
            stat_type="sd",
            unit="m/s",
        ),
        SensorColumn(
            column_name="WS_140m_sd",
            sensor_type="WindSpeed",
            sensor_direction="N",
            height=140.0,
            stat_type="sd",
            unit="m/s",
        ),
        # WindDirection sensors
        SensorColumn(
            column_name="WD_80m_avg",
            sensor_type="WindDirection",
            sensor_direction="N",
            height=80.0,
            stat_type="avg",
            unit="deg",
        ),
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
            column_name="WD_140m_avg",
            sensor_type="WindDirection",
            sensor_direction="N",
            height=140.0,
            stat_type="avg",
            unit="deg",
        ),
    ]


@pytest.fixture
def sample_wt_timeseries_mast():
    """Create a sample WtTimeSeriesMast configuration."""
    return WtTimeSeriesMast(
        name="TGL1",
        input=TimeSeriesSource(data="./representative-year/filled/TGL1.parquet"),
        csv_heights=[100.0, 120.0, 140.0],
        turbulence_heights=[80.0, 100.0, 120.0],
    )


@pytest.fixture
def sample_parquet_with_sensors(tmp_path, sample_sensor_columns_with_sd):
    """Create a sample parquet file with embedded sensor metadata."""
    import pyarrow.parquet as pq
    import pyarrow as pa

    np.random.seed(42)
    n = 1000

    # Generate timestamps
    timestamps = pl.datetime_range(
        start=pl.datetime(2023, 1, 1, 0, 0, 0),
        end=pl.datetime(2023, 1, 10, 0, 0, 0),
        interval="10m",
        eager=True,
    )[:n]

    # Generate realistic wind data
    base_speed = 8.0
    alpha = 0.14

    ws_80m = base_speed + np.random.normal(0, 1.5, n)
    ws_100m = base_speed * (100 / 80) ** alpha + np.random.normal(0, 1.5, n)
    ws_120m = base_speed * (120 / 80) ** alpha + np.random.normal(0, 1.5, n)
    ws_140m = base_speed * (140 / 80) ** alpha + np.random.normal(0, 1.5, n)

    # Generate SD values (TI ~ 0.15)
    ws_80m_sd = ws_80m * 0.15 + np.random.normal(0, 0.3, n)
    ws_100m_sd = ws_100m * 0.15 + np.random.normal(0, 0.3, n)
    ws_120m_sd = ws_120m * 0.15 + np.random.normal(0, 0.3, n)
    ws_140m_sd = ws_140m * 0.15 + np.random.normal(0, 0.3, n)

    # Generate wind directions
    base_dir = 180.0
    wd_80m = (base_dir + np.random.normal(0, 10, n)) % 360
    wd_100m = (base_dir + 0.5 + np.random.normal(0, 10, n)) % 360
    wd_120m = (base_dir + 1.0 + np.random.normal(0, 10, n)) % 360
    wd_140m = (base_dir + 1.5 + np.random.normal(0, 10, n)) % 360

    df = pl.DataFrame({
        "timestamp": timestamps,
        "WS_80m_avg": np.clip(ws_80m, 0, 50),
        "WS_100m_avg": np.clip(ws_100m, 0, 50),
        "WS_120m_avg": np.clip(ws_120m, 0, 50),
        "WS_140m_avg": np.clip(ws_140m, 0, 50),
        "WS_80m_sd": np.clip(ws_80m_sd, 0.01, 10),
        "WS_100m_sd": np.clip(ws_100m_sd, 0.01, 10),
        "WS_120m_sd": np.clip(ws_120m_sd, 0.01, 10),
        "WS_140m_sd": np.clip(ws_140m_sd, 0.01, 10),
        "WD_80m_avg": wd_80m,
        "WD_100m_avg": wd_100m,
        "WD_120m_avg": wd_120m,
        "WD_140m_avg": wd_140m,
    })

    parquet_path = tmp_path / "TGL1.parquet"

    # Convert to Arrow table
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
        for s in sample_sensor_columns_with_sd
    ]
    sensors_json = json.dumps({"sensors": sensors_list})

    # Write with metadata
    writer = pq.ParquetWriter(parquet_path, table.schema)
    writer.add_key_value_metadata({"cleanmast_sensors": sensors_json})
    writer.write_table(table)
    writer.close()

    return parquet_path, sample_sensor_columns_with_sd


@pytest.fixture
def ti_test_dataframe():
    """Create a test DataFrame for TI calculations."""
    np.random.seed(42)
    n = 10000

    # Wind speeds from 0 to 30 m/s with clustering
    wind_speeds = np.clip(np.random.weibull(2, n) * 8, 0.1, 30)

    # TI that decreases with wind speed (realistic behavior)
    target_ti = 0.2 / np.sqrt(wind_speeds / 5 + 0.5)
    wind_speed_sd = wind_speeds * target_ti + np.random.normal(0, 0.1, n)
    wind_speed_sd = np.clip(wind_speed_sd, 0.01, None)

    # Wind directions distributed across all sectors
    wind_directions = np.random.uniform(0, 360, n)

    return pl.DataFrame({
        "WS_80m_avg": wind_speeds,
        "WS_80m_sd": wind_speed_sd,
        "WD_80m_avg": wind_directions,
    })


@pytest.fixture
def known_ti_dataframe():
    """Create a DataFrame with known TI values for accuracy testing."""
    np.random.seed(42)
    n = 5000

    # Constant wind speed
    ws_avg = 10.0

    # Target TI = 0.15
    target_ti = 0.15
    ws_sd_mean = ws_avg * target_ti

    # Generate SD with small random variation
    ws_sd = ws_sd_mean + np.random.normal(0, 0.1, n)
    ws_sd = np.clip(ws_sd, 0.5, None)

    # Fixed direction
    wd = 180.0

    return pl.DataFrame({
        "wind_speed": np.full(n, ws_avg),
        "wind_speed_sd": ws_sd,
        "wind_direction": np.full(n, wd),
    }), target_ti
