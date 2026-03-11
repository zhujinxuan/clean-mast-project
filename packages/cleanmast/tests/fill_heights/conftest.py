"""Fixtures for fill_heights module tests."""

import numpy as np
import polars as pl
import pytest

from cleanmast.subdomains.configuration import (
    HeightReference,
    MastFillConfig,
    WindDirectionHeightConfig,
    WindSpeedHeightConfig,
)
from cleanmast.subdomains.dataingestion.value_objects import SensorColumn
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import TimeSeriesSource


@pytest.fixture
def sample_sensor_columns() -> list[SensorColumn]:
    """Create sample sensor columns for testing."""
    return [
        # WindSpeed sensors at different heights
        SensorColumn(
            column_name="WS_50m_avg",
            sensor_type="WindSpeed",
            sensor_direction="N",
            height=50.0,
            stat_type="avg",
            unit="m/s",
        ),
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
        # WindDirection sensors at different heights
        SensorColumn(
            column_name="WD_50m_avg",
            sensor_type="WindDirection",
            sensor_direction="N",
            height=50.0,
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
        SensorColumn(
            column_name="WD_100m_avg",
            sensor_type="WindDirection",
            sensor_direction="N",
            height=100.0,
            stat_type="avg",
            unit="deg",
        ),
        # Non-avg sensors (should be excluded from calculations)
        SensorColumn(
            column_name="WS_80m_max",
            sensor_type="WindSpeed",
            sensor_direction="N",
            height=80.0,
            stat_type="max",
            unit="m/s",
        ),
    ]


@pytest.fixture
def sample_timeseries(sample_sensor_columns: list[SensorColumn]) -> TimeSeriesData:
    """Create sample timeseries data for testing."""
    np.random.seed(42)
    n = 1000

    # Create timestamp column
    timestamps = pl.datetime_range(
        start=pl.datetime(2023, 1, 1, 0, 0, 0),
        end=pl.datetime(2023, 1, 10, 0, 0, 0),
        interval="10m",
        eager=True,
    )
    # Ensure we have exactly n timestamps
    if len(timestamps) >= n:
        timestamps = timestamps[:n]
    else:
        # If range is too short, extend with additional timestamps
        from datetime import timedelta
        last_ts = timestamps[-1]
        additional = pl.datetime_range(
            start=last_ts + timedelta(minutes=10),
            end=last_ts + timedelta(minutes=10 * (n - len(timestamps))),
            interval="10m",
            eager=True,
        )
        timestamps = pl.concat([timestamps, additional])

    # Generate wind speed data with realistic shear profile
    # Higher winds at higher altitudes
    base_speed = 8.0  # m/s at reference height
    alpha = 0.14  # shear exponent

    ws_50m = base_speed * (50 / 80) ** alpha + np.random.normal(0, 0.5, n)
    ws_80m = base_speed + np.random.normal(0, 0.5, n)
    ws_100m = base_speed * (100 / 80) ** alpha + np.random.normal(0, 0.5, n)

    # Generate wind direction data with slight veer (change with height)
    base_dir = 180.0  # South
    veer_rate = 0.05  # deg/m

    wd_50m = (base_dir - veer_rate * (80 - 50) + np.random.normal(0, 5, n)) % 360
    wd_80m = (base_dir + np.random.normal(0, 5, n)) % 360
    wd_100m = (base_dir + veer_rate * (100 - 80) + np.random.normal(0, 5, n)) % 360

    df = pl.DataFrame({
        "timestamp": timestamps,
        "WS_50m_avg": ws_50m,
        "WS_80m_avg": ws_80m,
        "WS_100m_avg": ws_100m,
        "WD_50m_avg": wd_50m,
        "WD_80m_avg": wd_80m,
        "WD_100m_avg": wd_100m,
    })

    return TimeSeriesData(df=df, sensors=sample_sensor_columns)


@pytest.fixture
def sample_mast_config() -> MastFillConfig:
    """Create sample mast configuration for testing."""
    return MastFillConfig(
        name="M01",
        input=TimeSeriesSource(
            data="./input/M01.parquet",
            sensors="./input/M01.sensors.yaml",
        ),
        output=TimeSeriesSource(
            data="./output/M01.parquet",
            sensors="./output/M01.sensors.yaml",
        ),
        windspeed=[
            WindSpeedHeightConfig(
                target_sensor=SensorColumn(
                    column_name="WS_120m_fill:extrapolated",
                    sensor_type="WindSpeed",
                    sensor_direction="N/A",
                    height=120.0,
                    stat_type="avg",
                    unit="m/s",
                ),
                references=[
                    HeightReference(
                        sensor=SensorColumn(
                            column_name="WS_100m_avg",
                            sensor_type="WindSpeed",
                            sensor_direction="N",
                            height=100.0,
                            stat_type="avg",
                            unit="m/s",
                        ),
                        weight=1.0,
                    ),
                ],
                shear=0.14,
            ),
        ],
        winddirection=[
            WindDirectionHeightConfig(
                target_sensor=SensorColumn(
                    column_name="WD_120m_fill:extrapolated",
                    sensor_type="WindDirection",
                    sensor_direction="N/A",
                    height=120.0,
                    stat_type="avg",
                    unit="deg",
                ),
                references=[
                    HeightReference(
                        sensor=SensorColumn(
                            column_name="WD_100m_avg",
                            sensor_type="WindDirection",
                            sensor_direction="N",
                            height=100.0,
                            stat_type="avg",
                            unit="deg",
                        ),
                        weight=1.0,
                    ),
                ],
                deg_diff_per_m=0.05,
            ),
        ],
    )


@pytest.fixture
def sample_interpolation_ws_config() -> WindSpeedHeightConfig:
    """Create sample WS interpolation config."""
    return WindSpeedHeightConfig(
        target_sensor=SensorColumn(
            column_name="WS_65m_fill:interpolated",
            sensor_type="WindSpeed",
            sensor_direction="N/A",
            height=65.0,
            stat_type="avg",
            unit="m/s",
        ),
        references=[
            HeightReference(
                sensor=SensorColumn(
                    column_name="WS_50m_avg",
                    sensor_type="WindSpeed",
                    sensor_direction="N",
                    height=50.0,
                    stat_type="avg",
                    unit="m/s",
                ),
                weight=0.6,
            ),
            HeightReference(
                sensor=SensorColumn(
                    column_name="WS_80m_avg",
                    sensor_type="WindSpeed",
                    sensor_direction="N",
                    height=80.0,
                    stat_type="avg",
                    unit="m/s",
                ),
                weight=0.4,
            ),
        ],
        shear=0.14,
    )


@pytest.fixture
def sample_interpolation_wd_config() -> WindDirectionHeightConfig:
    """Create sample WD interpolation config."""
    return WindDirectionHeightConfig(
        target_sensor=SensorColumn(
            column_name="WD_65m_fill:interpolated",
            sensor_type="WindDirection",
            sensor_direction="N/A",
            height=65.0,
            stat_type="avg",
            unit="deg",
        ),
        references=[
            HeightReference(
                sensor=SensorColumn(
                    column_name="WD_50m_avg",
                    sensor_type="WindDirection",
                    sensor_direction="N",
                    height=50.0,
                    stat_type="avg",
                    unit="deg",
                ),
                weight=0.6,
            ),
            HeightReference(
                sensor=SensorColumn(
                    column_name="WD_80m_avg",
                    sensor_type="WindDirection",
                    sensor_direction="N",
                    height=80.0,
                    stat_type="avg",
                    unit="deg",
                ),
                weight=0.4,
            ),
        ],
        deg_diff_per_m=0.05,
    )


@pytest.fixture
def known_shear_timeseries() -> TimeSeriesData:
    """Create timeseries with known shear for testing."""
    sensors = [
        SensorColumn(
            column_name="WS_50m_avg",
            sensor_type="WindSpeed",
            sensor_direction="N",
            height=50.0,
            stat_type="avg",
            unit="m/s",
        ),
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
    ]

    # Create perfectly power-law wind profile with known shear
    alpha = 0.20  # Known shear exponent
    v_ref = 10.0  # Wind speed at 80m

    n = 100
    v_50m = np.full(n, v_ref * (50 / 80) ** alpha)
    v_80m = np.full(n, v_ref)
    v_100m = np.full(n, v_ref * (100 / 80) ** alpha)

    df = pl.DataFrame({
        "timestamp": pl.datetime_range(
            start=pl.datetime(2023, 1, 1),
            end=pl.datetime(2023, 1, 2),
            interval="10m",
            eager=True,
        )[:n],
        "WS_50m_avg": v_50m,
        "WS_80m_avg": v_80m,
        "WS_100m_avg": v_100m,
    })

    return TimeSeriesData(df=df, sensors=sensors)


@pytest.fixture
def wraparound_wd_timeseries() -> TimeSeriesData:
    """Create timeseries with wraparound wind directions for testing."""
    sensors = [
        SensorColumn(
            column_name="WD_50m_avg",
            sensor_type="WindDirection",
            sensor_direction="N",
            height=50.0,
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
    ]

    # Create data with wraparound scenario
    # Low level: 355° (just west of north)
    # High level: 5° (just east of north)
    # True veer is +10° (clockwise), not -350°
    n = 100
    wd_50m = np.full(n, 355.0)
    wd_100m = np.full(n, 5.0)

    df = pl.DataFrame({
        "timestamp": pl.datetime_range(
            start=pl.datetime(2023, 1, 1),
            end=pl.datetime(2023, 1, 2),
            interval="10m",
            eager=True,
        )[:n],
        "WD_50m_avg": wd_50m,
        "WD_100m_avg": wd_100m,
    })

    return TimeSeriesData(df=df, sensors=sensors)
