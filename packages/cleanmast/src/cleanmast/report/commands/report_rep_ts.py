"""Report rep-ts command.

This module provides the CLI command for generating representative timeseries reports
from processed mast data.
"""

from pathlib import Path

import click
import polars as pl

from ...io import load_timeseries
from ...models.sensor import SensorColumn
from ...models.timeseries import TimeSeriesSource
from ..atoms.single_mast.monthly_wind import SingleMastMonthlyWindAtom
from ..atoms.single_mast.monthly_wind_power import SingleMastMonthlyWindPowerAtom
from ..atoms.single_mast.schemas import (
    MonthlyWindPowerSchema,
    MonthlyWindSchema,
    WindRoseSchema,
)
from ..atoms.single_mast.wind_rose import (
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
)
from ..builder import ReportBuilder
from ..collection import AtomCollection
from ..config import RepTsReportConfig
from ..meta import SingleMastMeta, detect_interpolation_marker
from ..sections import (
    RepresentativeWindPowerSection,
    RepresentativeWindSpeedSection,
    TemplatedSection,
    WindRoseSection,
    WIND_SPEED_POWER_TEMPLATE,
)

# Sector definitions for wind rose (16 sectors, 22.5° each)
SECTOR_NAMES = [
    "N", "NNE", "NE", "ENE",
    "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW",
    "W", "WNW", "NW", "NNW",
]


def process_monthly_wind_data(
    df: pl.DataFrame,
    sensors: list[SensorColumn],
) -> pl.DataFrame:
    """Process data into monthly wind statistics (long format).

    For each height, calculate monthly mean/max/min wind speed.

    Args:
        df: DataFrame with timestamp and WS_* columns
        sensors: List of SensorColumn objects for wind speed sensors

    Returns:
        DataFrame with columns: month, height, interpolation_marker,
        wind_speed_mean, wind_speed_max, wind_speed_min
    """
    # Add month column
    df = df.with_columns(pl.col("timestamp").dt.month().alias("month"))

    # Process each height
    rows: list[dict] = []
    for sensor in sensors:
        height = sensor.height
        ws_col = sensor.column_name

        # Get interpolation marker from column name
        marker = detect_interpolation_marker(ws_col)

        # Calculate monthly statistics for this height
        monthly_stats = df.group_by("month").agg([
            pl.col(ws_col).mean().alias("wind_speed_mean"),
            pl.col(ws_col).max().alias("wind_speed_max"),
            pl.col(ws_col).min().alias("wind_speed_min"),
        ]).sort("month")

        # Convert to rows
        for row in monthly_stats.iter_rows(named=True):
            rows.append({
                "month": row["month"],
                "height": height,
                "interpolation_marker": marker,
                "wind_speed_mean": row["wind_speed_mean"],
                "wind_speed_max": row["wind_speed_max"],
                "wind_speed_min": row["wind_speed_min"],
            })

    return pl.DataFrame(rows)


def process_monthly_wind_power_data(
    df: pl.DataFrame,
    heights_info: list[tuple[float, str]],
    air_density: float,
) -> pl.DataFrame:
    """Process data into monthly wind power density statistics (long format).

    For each height, calculate monthly wind power density using 0.5 * ρ * WS³.

    Args:
        df: DataFrame with timestamp and WS_* columns
        heights_info: List of (height, column_name) tuples
        air_density: Air density in kg/m³

    Returns:
        DataFrame with columns: month, height, interpolation_marker,
        wind_power_density, air_density_used
    """
    # Add month column
    df = df.with_columns(pl.col("timestamp").dt.month().alias("month"))

    # Process each height
    rows: list[dict] = []
    for height, ws_col in heights_info:
        # Get interpolation marker from column name
        marker = detect_interpolation_marker(ws_col)

        # Calculate monthly power density for this height
        # Power density = 0.5 * ρ * WS³
        monthly_stats = df.group_by("month").agg([
            (0.5 * air_density * pl.col(ws_col) ** 3).mean().alias("wind_power_density"),
        ]).sort("month")

        # Convert to rows
        for row in monthly_stats.iter_rows(named=True):
            rows.append({
                "month": row["month"],
                "height": height,
                "interpolation_marker": marker,
                "wind_power_density": row["wind_power_density"],
                "air_density_used": air_density,
            })

    return pl.DataFrame(rows)


def process_wind_rose_data(
    df: pl.DataFrame,
    heights_info: list[tuple[float, str]],
    wd_columns: list[tuple[float, str]],
    air_density: float,
) -> pl.DataFrame:
    """Process data into wind rose statistics (long format).

    For each height, calculate sector frequencies and power densities.

    Args:
        df: DataFrame with timestamp, WS_*, and WD_* columns
        heights_info: List of (height, ws_column_name) tuples
        wd_columns: List of (height, wd_column_name) tuples
        air_density: Air density in kg/m³

    Returns:
        DataFrame with columns: sector, sector_name, height, interpolation_marker,
        frequency, wind_power_density
    """
    # Create mapping from height to WD column
    wd_col_map: dict[float, str] = {height: col for height, col in wd_columns}

    rows: list[dict] = []

    for height, ws_col in heights_info:
        # Get corresponding WD column for this height
        wd_col = wd_col_map.get(height)
        if wd_col is None:
            click.echo(f"  Warning: No wind direction column found for height {height}m")
            continue

        # Get interpolation marker from column name
        marker = detect_interpolation_marker(ws_col)

        # Filter out null wind direction values before processing
        valid_df = df.filter(pl.col(wd_col).is_not_null())

        # Calculate sector (0-15) from wind direction
        df_with_sector = valid_df.with_columns(
            ((pl.col(wd_col) / 22.5).round().cast(pl.Int64) % 16).alias("sector")
        )

        # Group by sector and calculate statistics
        sector_stats = df_with_sector.group_by("sector").agg([
            pl.len().alias("count"),
            (0.5 * air_density * pl.col(ws_col) ** 3).mean().alias("wind_power_density"),
        ]).sort("sector")

        # Calculate frequency based on valid (non-null) rows
        valid_row_count = len(valid_df)

        # Convert to rows with frequency and sector names
        for row in sector_stats.iter_rows(named=True):
            sector = int(row["sector"])
            frequency = row["count"] / valid_row_count
            power_density = row["wind_power_density"]

            rows.append({
                "sector": sector,
                "sector_name": SECTOR_NAMES[sector],
                "height": height,
                "interpolation_marker": marker,
                "frequency": frequency,
                "wind_power_density": power_density,
            })

    return pl.DataFrame(rows)


@click.command("rep-ts")
@click.argument("project_dir", type=click.Path(exists=True))
@click.option(
    "--no-pdf",
    is_flag=True,
    help="Skip PDF generation (not recommended)",
)
@click.option(
    "--no-docx",
    is_flag=True,
    help="Skip DOCX generation",
)
def report_rep_ts(project_dir: str, no_pdf: bool, no_docx: bool):
    """Generate representative timeseries report from config.

    This command:
    1. Reads rep-ts-report.toml from the project directory
    2. For each mast, loads the parquet file specified in config
    3. Processes data to create all 4 report atoms (monthly wind, monthly power,
       wind frequency rose, wind power rose)
    4. Generates a complete Typst report with images and tables

    Prerequisites:
    - rep-ts-report.toml must exist in project directory
    - Parquet files must exist at paths specified in config

    Args:
        project_dir: Path to project directory containing rep-ts-report.toml

    Outputs:
        - {project_dir}/rep-ts/report.typ: Complete Typst report
        - {project_dir}/rep-ts/images/*.png: Generated chart images

    Example:
        uv run cleanmast report rep-ts projects/my-project

    Config format (rep-ts-report.toml):
        [[masts]]
        name = "M6002"

        [masts.input]
        data = "./representative-year-fill-heights/M6002.parquet"
        air_density = 1.189
    """
    project_path = Path(project_dir)

    # Load and validate config
    config_path = project_path / "rep-ts-report.toml"
    if not config_path.exists():
        raise click.ClickException(
            f"rep-ts-report.toml not found at {config_path}. "
            "Run 'recommend rep-ts-report' command first."
        )

    config = RepTsReportConfig.from_toml(config_path)

    masts_config = config.masts
    if not masts_config:
        raise click.ClickException("No masts found in rep-ts-report.toml")

    click.echo(f"Processing {len(masts_config)} masts for representative year report...")

    # Create output directory
    output_dir = project_path / "rep-ts"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create report builder
    builder = ReportBuilder("代表年测风报告", output_dir)

    # Dictionary to collect atoms from all masts
    all_mast_atoms: dict[str, list] = {}

    # Process each mast
    for mast in masts_config:
        mast_name = mast.name
        air_density = mast.air_density

        click.echo(f"\nProcessing {mast_name}...")
        click.echo(f"  Data: {mast.input.data}")
        click.echo(f"  Air density: {air_density} kg/m³")

        try:
            # Load timeseries with sensor metadata
            timeseries = load_timeseries(mast.input, str(project_path))
            df = timeseries.df
            sensors = timeseries.sensors

            click.echo(f"  Loaded {len(df)} rows with {len(sensors)} sensors")

            # Filter sensors by type and ensure column exists in DataFrame
            df_columns = set(df.columns)
            wind_speed_sensors = [
                s for s in sensors
                if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
                and s.column_name in df_columns
            ]
            wind_dir_sensors = [
                s for s in sensors
                if s.sensor_type == "WindDirection" and s.stat_type == "avg"
                and s.column_name in df_columns
            ]

            # Map to (height, column_name) tuples for processing
            ws_heights = [(s.height, s.column_name) for s in wind_speed_sensors]
            wd_heights = [(s.height, s.column_name) for s in wind_dir_sensors]
            ws_heights.sort(key=lambda x: x[0])
            wd_heights.sort(key=lambda x: x[0])

            if not ws_heights:
                click.echo(f"  Warning: No wind speed sensors found, skipping")
                continue

            click.echo(f"  Found {len(ws_heights)} wind speed sensor(s)")
            if wd_heights:
                click.echo(f"  Found {len(wd_heights)} wind direction sensor(s)")

            # Create metadata
            meta = SingleMastMeta(
                mast_name=mast_name,
                air_density=air_density,
                caption=f"{mast_name} 测风数据分析",
                width="80%",
            )

            # Process data for each atom type
            click.echo("  Processing monthly wind data...")
            monthly_wind_df = process_monthly_wind_data(df, wind_speed_sensors)
            monthly_wind_atom = SingleMastMonthlyWindAtom.create(
                MonthlyWindSchema, monthly_wind_df, meta
            )

            click.echo("  Processing monthly wind power data...")
            monthly_power_df = process_monthly_wind_power_data(
                df, ws_heights, air_density
            )
            monthly_power_atom = SingleMastMonthlyWindPowerAtom.create(
                MonthlyWindPowerSchema, monthly_power_df, meta
            )

            # Only create wind rose atoms if we have wind direction data
            wind_freq_atom = None
            wind_power_atom = None

            if wd_heights:
                click.echo("  Processing wind rose data...")
                wind_rose_df = process_wind_rose_data(
                    df, ws_heights, wd_heights, air_density
                )
                wind_freq_atom = SingleMastMonthlyWindFrequencyRoseAtom.create(
                    WindRoseSchema, wind_rose_df, meta
                )
                wind_power_atom = SingleMastWindPowerRoseAtom.create(
                    WindRoseSchema, wind_rose_df, meta
                )
            else:
                click.echo("  Skipping wind rose (no wind direction data)")

            # Store atoms for this mast (will combine later)
            mast_atoms = [monthly_wind_atom, monthly_power_atom]
            if wind_freq_atom:
                mast_atoms.append(wind_freq_atom)
            if wind_power_atom:
                mast_atoms.append(wind_power_atom)
            all_mast_atoms[mast_name] = mast_atoms

            click.echo(f"  ✓ Processed data for {mast_name}")

        except Exception as e:
            click.echo(f"  Error processing {mast_name}: {e}")
            raise click.ClickException(f"Failed to process mast {mast_name}: {e}")

    # Create combined collection with all masts
    click.echo("\nCreating representative year sections...")
    combined_collection = AtomCollection.from_dict(all_mast_atoms)

    # Add representative year wind speed section
    speed_section = RepresentativeWindSpeedSection(
        atoms=combined_collection,
        title="代表年各月风速结果",
        level=1
    )
    builder.add_section(speed_section)

    # Add representative year wind power section
    power_section = RepresentativeWindPowerSection(
        atoms=combined_collection,
        title="代表年各月风功率结果",
        level=1
    )
    builder.add_section(power_section)

    click.echo(f"  ✓ Added representative year sections ({len(all_mast_atoms)} masts)")

    # Generate report
    click.echo("\nGenerating report...")
    try:
        results = builder.build(
            compile_pdf=not no_pdf,
            compile_docx=not no_docx,
        )

        click.echo("\n✓ Report generated successfully!")
        click.echo(f"  Typst: {results['typ']}")

        if "pdf" in results:
            click.echo(f"  PDF:   {results['pdf']}")

        if "docx" in results:
            click.echo(f"  DOCX:  {results['docx']}")

        if "docx_warning" in results:
            click.echo(f"\n⚠ Warning: {results['docx_warning']}")
    except RuntimeError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Failed to generate report: {e}")
