"""Execute fill-heights command.

This module provides the CLI command for executing fill-heights operations
from configuration files.
"""

from pathlib import Path

import click

from ..config import load_fill_heights_config
from ..recommend.validation import _validate_references
from ..execute.ws import apply_ws_fill
from ..execute.wd import apply_wd_fill
from ...io.timeseries_io import load_timeseries, save_timeseries
from ...models.sensor import SensorColumn
from ...models.timeseries import TimeSeriesData


@click.command()
@click.argument("config_path", type=click.Path(exists=True))
def fill_heights(config_path: str):
    """Execute fill-heights from configuration file.

    This command:
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

    Example:
        uv run cleanmast fill-heights projects/my-project/fill-heights-reconstruct-meso.toml

    Output:
        - {output.data}: Timeseries with filled columns added
        - {output.sensors}: Updated sensor metadata
    """
    config_path_obj = Path(config_path)
    base_dir = str(config_path_obj.parent)

    click.echo(f"Loading config: {config_path}")
    config = load_fill_heights_config(str(config_path_obj))

    click.echo(f"Strategy: {config.strategy}")
    click.echo(f"Masts: {len(config.masts)}")

    # Process each mast
    for mast_config in config.masts:
        click.echo(f"\nProcessing mast: {mast_config.name}")

        # Load input timeseries
        click.echo(f"  Loading input: {mast_config.input.data}")
        timeseries = load_timeseries(mast_config.input, base_dir)
        click.echo(f"  Loaded {len(timeseries.df)} rows with {len(timeseries.sensors)} sensors")

        # Validate reference configurations against sensor metadata
        click.echo("  Validating reference configurations...")
        _validate_references(timeseries, mast_config)
        click.echo("  Reference validation passed")

        # Start with original dataframe and sensors
        new_columns = []
        new_sensors = list(timeseries.sensors)

        # Apply wind speed fills
        for ws_config in mast_config.windspeed:
            click.echo(f"  Filling wind speed: {ws_config.target_column}")
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
            click.echo(f"    Added column with {filled_series.is_null().sum()} null values")

        # Apply wind direction fills
        for wd_config in mast_config.winddirection:
            click.echo(f"  Filling wind direction: {wd_config.target_column}")
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
            click.echo(f"    Added column with {filled_series.is_null().sum()} null values")

        # Add new columns to dataframe
        if new_columns:
            df_with_fills = timeseries.df.with_columns(new_columns)
            output_timeseries = TimeSeriesData(df=df_with_fills, sensors=new_sensors)
        else:
            output_timeseries = timeseries

        # Save output
        click.echo(f"  Saving output: {mast_config.output.data}")
        save_timeseries(mast_config.output, base_dir, output_timeseries)

        # Count filled columns
        ws_fills = len(mast_config.windspeed)
        wd_fills = len(mast_config.winddirection)
        click.echo(f"  Complete: {ws_fills} wind speed + {wd_fills} wind direction columns")

    click.echo("\nFill-heights complete!")
