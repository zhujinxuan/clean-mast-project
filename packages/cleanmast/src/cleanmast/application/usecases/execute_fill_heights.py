"""Execute fill-heights use case.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-a-001-use-case-pattern
Compliance: Subdomain layout ✓ | Use Case ✓ | CLI Adapter Ready ✓
Description: Application use case for executing fill-heights operations from configuration files

This module provides the use case for executing fill-heights operations
from configuration files.
"""

from pathlib import Path

from cleanmast.infrastructure.path_utils import to_posix_path
from cleanmast.shared.timeseries import TimeSeriesData
from cleanmast.shared.timeseries.io.file_repository import FileTimeSeriesRepository
from cleanmast.shared.timeseries.sensor_column import SensorColumn
from cleanmast.subdomains.dataprocessing.services.height_filler import (
    apply_wd_fill,
    apply_ws_fill,
)
from cleanmast.subdomains.dataprocessing.services.height_filling.validation import (
    _validate_references,
)


def execute_fill_heights(config_path: str) -> None:
    """Execute fill-heights from configuration file.

    This use case:
    1. Loads the fill-heights configuration
    2. Loads input timeseries data for each mast
    3. Applies wind speed and direction filling
    4. Saves output with new columns

    The configuration specifies:
    - Input data source (parquet + sensors yaml)
    - Output destination
    - Wind speed fill configurations (target, references, shear)
    - Wind direction fill configurations (target, references, deg_diff)

    Processing:
    - For each mast:
        a. Load input timeseries
        b. Apply WS fills using power law extrapolation/interpolation
        c. Apply WD fills using vector-based interpolation
        d. Add new sensor metadata
        e. Save output

    Args:
        config_path: Path to fill-heights-*.toml configuration file

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is invalid
    """
    from cleanmast.shared.timeseries.fill_height_config import (
        FillHeightsConfiguration,
    )
    from cleanmast.subdomains.configuration import load_config

    config = load_config(FillHeightsConfiguration, config_path)
    base_dir = to_posix_path(Path(config_path).parent)

    # Process each mast
    for mast_config in config.masts:
        # Load input timeseries
        repo = FileTimeSeriesRepository()
        timeseries = repo.load(mast_config.input, base_dir)
        # Validate reference configurations against sensor metadata
        _validate_references(timeseries, mast_config)

        # Start with original dataframe and sensors
        new_columns = []
        new_sensors = list(timeseries.sensors)

        # Apply wind speed fills
        for ws_config in mast_config.windspeed:
            target_height = ws_config.target_height
            filled_series = apply_ws_fill(
                timeseries.df,
                ws_config.target_sensor,
                ws_config.references,
                ws_config.shear,
            )
            new_columns.append(filled_series)

            # Create sensor metadata for new column
            sensor = SensorColumn(
                column_name=ws_config.target_column,
                sensor_type="WindSpeed",
                sensor_direction="N/A",
                height=target_height,
                stat_type="avg",
                unit="m/s",
            )
            new_sensors.append(sensor)

        # Apply wind direction fills
        for wd_config in mast_config.winddirection:
            target_height = wd_config.target_height
            filled_series = apply_wd_fill(
                timeseries.df,
                wd_config.target_sensor,
                wd_config.references,
                wd_config.deg_diff_per_m,
            )
            new_columns.append(filled_series)

            # Create sensor metadata for new column
            sensor = SensorColumn(
                column_name=wd_config.target_column,
                sensor_type="WindDirection",
                sensor_direction="N/A",
                height=target_height,
                stat_type="avg",
                unit="deg",
            )
            new_sensors.append(sensor)

        # Add new columns to dataframe
        if new_columns:
            df_with_fills = timeseries.df.with_columns(new_columns)
            output_timeseries = TimeSeriesData(df=df_with_fills, sensors=new_sensors)
        else:
            output_timeseries = timeseries

        # Save output
        repo.save(mast_config.output, base_dir, output_timeseries)
