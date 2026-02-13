"""Wind extrapolation execution.

Functions for executing vertical wind extrapolation based on configuration.
"""

from pathlib import Path

import polars as pl

from ..io.timeseries_io import load_timeseries, save_timeseries
from ..models.sensor import SensorColumn
from ..models.timeseries import TimeSeriesData
from .config import MastExtrapolateConfig, load_extrapolate_config
from .shear import extrapolate_wind_direction, extrapolate_wind_speed


def extrapolate_mast(
    timeseries: TimeSeriesData,
    mast_config: MastExtrapolateConfig,
) -> TimeSeriesData:
    """Extrapolate wind speed and direction for a single mast.

    Args:
        timeseries: Input time series data
        mast_config: Per-mast extrapolation configuration

    Returns:
        TimeSeriesData with extrapolated columns added
    """
    df = timeseries.df.clone()
    new_sensors: list[SensorColumn] = list(timeseries.sensors)

    # Find reference sensors in the data
    sensor_by_height_type: dict[tuple[float, str], SensorColumn] = {}
    for sensor in timeseries.sensors:
        if sensor.stat_type == "avg":
            key = (sensor.height, sensor.sensor_type)
            sensor_by_height_type[key] = sensor

    # Extrapolate wind speed for each target height
    for ws_height_config in mast_config.windspeed.heights:
        target_height = ws_height_config.height

        # For now, use first reference (single reference strategy)
        # TODO: Support weighted averaging of multiple references
        if not ws_height_config.references:
            continue

        ref = ws_height_config.references[0]
        ref_height = ref.height
        shear = ref.shear

        # Find reference sensor
        ref_sensor = sensor_by_height_type.get((ref_height, "WindSpeed"))
        if ref_sensor is None:
            # Try to find closest height
            ws_sensors = [
                s for s in timeseries.sensors
                if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
            ]
            if not ws_sensors:
                continue
            # Use sensor closest to reference height
            ref_sensor = min(ws_sensors, key=lambda s: abs(s.height - ref_height))

        # Extrapolate wind speed
        ref_col = ref_sensor.column_name
        if ref_col in df.columns:
            new_col_name = f"WS_{int(target_height)}m_extrapolated"
            extrapolated = extrapolate_wind_speed(
                wind_speed=df[ref_col].to_numpy(),
                reference_height=ref_sensor.height,
                target_height=target_height,
                shear=shear,
            )
            df = df.with_columns(pl.Series(name=new_col_name, values=extrapolated))

            # Add sensor metadata
            new_sensors.append(
                SensorColumn(
                    column_name=new_col_name,
                    sensor_type="WindSpeed",
                    sensor_direction="",
                    height=target_height,
                    stat_type="avg",
                    unit="m/s",
                )
            )

    # Extrapolate wind direction for each target height
    for wd_height_config in mast_config.winddirection.heights:
        target_height = wd_height_config.height

        if not wd_height_config.references:
            continue

        ref = wd_height_config.references[0]
        ref_height = ref.height
        deg_diff_per_m = ref.deg_diff_per_m

        # Find reference sensor
        ref_sensor = sensor_by_height_type.get((ref_height, "WindDirection"))
        if ref_sensor is None:
            # Try to find closest height
            wd_sensors = [
                s for s in timeseries.sensors
                if s.sensor_type == "WindDirection" and s.stat_type == "avg"
            ]
            if not wd_sensors:
                continue
            ref_sensor = min(wd_sensors, key=lambda s: abs(s.height - ref_height))

        # Extrapolate wind direction
        ref_col = ref_sensor.column_name
        if ref_col in df.columns:
            new_col_name = f"WD_{int(target_height)}m_extrapolated"
            extrapolated = extrapolate_wind_direction(
                wind_direction=df[ref_col].to_numpy(),
                reference_height=ref_sensor.height,
                target_height=target_height,
                deg_diff_per_m=deg_diff_per_m,
            )
            df = df.with_columns(pl.Series(name=new_col_name, values=extrapolated))

            # Add sensor metadata
            new_sensors.append(
                SensorColumn(
                    column_name=new_col_name,
                    sensor_type="WindDirection",
                    sensor_direction="",
                    height=target_height,
                    stat_type="avg",
                    unit="deg",
                )
            )

    return TimeSeriesData(df=df, sensors=new_sensors)


def execute_extrapolation(config_path: str) -> None:
    """Execute vertical wind extrapolation from configuration file.

    Args:
        config_path: Path to vertical-extrapolate.toml file
    """
    config_path_obj = Path(config_path)
    base_dir = str(config_path_obj.parent)

    # Load configuration
    config = load_extrapolate_config(config_path)

    # Process each mast
    for mast_config in config.masts:
        # Load input timeseries
        timeseries = load_timeseries(mast_config.input, base_dir)

        # Extrapolate
        result = extrapolate_mast(timeseries, mast_config)

        # Save output
        save_timeseries(mast_config.output, base_dir, result)
