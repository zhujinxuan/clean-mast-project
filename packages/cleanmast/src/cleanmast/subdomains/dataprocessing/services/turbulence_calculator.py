"""Turbulence calculator service.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓

This module provides the domain service for calculating Turbulence Intensity (TI)
matrices from wind speed and direction data. TI is calculated as:

    TI = WS_sd / max(WS_avg, 1.0)

The module supports:
- TI series calculation from wind speed, standard deviation, and direction
- TI matrix generation binned by wind speed and direction sectors
- MeteoDyn format file generation for wind flow modeling software
"""

import logging
from pathlib import Path

import dataframely as dy
import polars as pl

from cleanmast.subdomains.configuration import (
    WtTimeSeriesMast,
)
from cleanmast.subdomains.dataingestion.repositories.parquet_repository import (
    ParquetRepository,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn

logger = logging.getLogger(__name__)

# 16 direction sectors, each 22.5 degrees
DIRECTION_16_SECTORS = [
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
]


class TIMatrixSchema(dy.Schema):
    """Schema for TI matrix DataFrame validation.

    This schema validates the structure of the TI (Turbulence Intensity) matrix
    returned by calculate_ti_matrix(). The matrix contains:
    - v_max: Wind speed bin upper bound
    - 16 direction sectors: Mean TI values (0-1 range)

    Example:
        >>> df = pl.DataFrame({
        ...     "v_max": [1.0, 2.0, 3.0],
        ...     "N": [0.1, 0.12, 0.15],
        ...     "NNE": [0.1, 0.12, 0.15],
        ...     # ... all 16 sectors
        ... })
        >>> validated = TIMatrixSchema.validate(df, cast=True)
    """

    v_max = dy.Float64(nullable=False)
    N = dy.Float64(nullable=False, min=0.0, max=1.0)
    NNE = dy.Float64(nullable=False, min=0.0, max=1.0)
    NE = dy.Float64(nullable=False, min=0.0, max=1.0)
    ENE = dy.Float64(nullable=False, min=0.0, max=1.0)
    E = dy.Float64(nullable=False, min=0.0, max=1.0)
    ESE = dy.Float64(nullable=False, min=0.0, max=1.0)
    SE = dy.Float64(nullable=False, min=0.0, max=1.0)
    SSE = dy.Float64(nullable=False, min=0.0, max=1.0)
    S = dy.Float64(nullable=False, min=0.0, max=1.0)
    SSW = dy.Float64(nullable=False, min=0.0, max=1.0)
    SW = dy.Float64(nullable=False, min=0.0, max=1.0)
    WSW = dy.Float64(nullable=False, min=0.0, max=1.0)
    W = dy.Float64(nullable=False, min=0.0, max=1.0)
    WNW = dy.Float64(nullable=False, min=0.0, max=1.0)
    NW = dy.Float64(nullable=False, min=0.0, max=1.0)
    NNW = dy.Float64(nullable=False, min=0.0, max=1.0)


def _direction_to_sector(wd_col: pl.Expr) -> pl.Expr:
    """Convert wind direction (0-360) to 16-sector index (0-15).

    Each sector is 22.5 degrees wide. The mapping is:
    - N: 0-22.5 degrees (sector 0)
    - NNE: 22.5-45 degrees (sector 1)
    - ...
    - NNW: 337.5-360 degrees (sector 15)

    Args:
        wd_col: Polars expression for wind direction column (0-360 degrees)

    Returns:
        Expression that evaluates to sector index (0-15)
    """
    # Sector = floor(direction / 22.5) mod 16
    return (wd_col / 22.5).floor().mod(16).cast(pl.Int32)


def calculate_ti_series(
    df: pl.DataFrame,
    ws_col: str,
    sd_col: str,
    wd_col: str,
) -> pl.DataFrame:
    """Calculate TI series from wind speed, SD, and direction.

    TI (Turbulence Intensity) is calculated as:
        TI = WS_sd / max(WS_avg, 1.0)

    The result is capped at 1.0 to avoid unrealistic values.

    Args:
        df: Input DataFrame with wind speed, SD, and direction columns
        ws_col: Column name for wind speed (average)
        sd_col: Column name for wind speed standard deviation
        wd_col: Column name for wind direction

    Returns:
        DataFrame with 'ti' and 'sector' columns.
        Only includes rows where all input values are valid (non-null).

    Example:
        >>> ti_df = calculate_ti_series(df, "wind_speed_80m", "wind_speed_sd_80m", "wind_dir_80m")
        >>> ti_df.head()
        shape: (5, 2)
        ┌───────┬────────┐
        │ ti    ┆ sector │
        │ ---   ┆ ---    │
        │ f64   ┆ i32    │
        ╞═══════╪════════╡
        │ 0.152 ┆ 0      │
        │ 0.089 ┆ 1      │
        │ 0.123 ┆ 0      │
        │ 0.201 ┆ 15     │
        │ 0.095 ┆ 2      │
        └───────┴────────┘
    """
    # Build TI expression: sd / max(ws, 1.0), capped at 1.0
    ws_expr = pl.col(ws_col)
    sd_expr = pl.col(sd_col)
    wd_expr = pl.col(wd_col)

    ti_expr = (sd_expr / pl.max_horizontal(ws_expr, pl.lit(1.0))).clip(upper_bound=1.0)
    sector_expr = _direction_to_sector(wd_expr)

    # Filter out nulls and select TI + sector columns
    result = (
        df.filter(
            ws_expr.is_not_null() & sd_expr.is_not_null() & wd_expr.is_not_null()
        )
        .select([
            ti_expr.alias("ti"),
            sector_expr.alias("sector"),
        ])
    )

    return result


def calculate_sector_stats(ti_df: pl.DataFrame) -> dict:
    """Calculate overall sector statistics from TI series.

    Computes the overall mean TI across all data points.

    Args:
        ti_df: TI series DataFrame with 'ti' and 'sector' columns

    Returns:
        Dictionary with mean_ti value across all data.
        Returns mean_ti=0.1 as fallback if no data available.

    Example:
        >>> stats = calculate_sector_stats(ti_df)
        >>> print(stats["mean_ti"])
        0.123
    """
    if ti_df.is_empty():
        return {"mean_ti": 0.1}

    # Calculate mean TI across all rows
    mean_ti = ti_df.select(pl.col("ti").mean()).item()

    # Handle None or NaN
    if mean_ti is None or (isinstance(mean_ti, float) and mean_ti != mean_ti):  # NaN check
        return {"mean_ti": 0.1}

    return {"mean_ti": float(mean_ti)}


def _create_wind_speed_bin(
    ws_values: pl.Series,
    bins: list[float],
) -> pl.Series:
    """Create wind speed bin indices from wind speed values.

    Assigns each wind speed value to the appropriate bin index.
    Bin i contains values where: bins[i-1] < value <= bins[i] (for i > 0)
    Bin 0 contains values where value <= bins[0]

    Args:
        ws_values: Series of wind speed values
        bins: List of bin upper bounds

    Returns:
        Series of bin indices (0-indexed)
    """
    # Use search_sorted to find bin for each value
    # search_sorted returns the index where value should be inserted to maintain order
    bin_series = pl.Series("bins", bins)
    return ws_values.search_sorted(bin_series, side="left")


def _create_wind_speed_bin_expr(
    ws_expr: pl.Expr,
    wind_speed_bins: list[float],
) -> pl.Expr:
    """Create a Polars expression for wind speed bin indexing.

    Creates a when/then expression chain that assigns each wind speed value
    to its corresponding bin index based on the bin upper bounds.

    Bin assignment:
    - Bin 0: values <= wind_speed_bins[0]
    - Bin i: wind_speed_bins[i-1] < value <= wind_speed_bins[i]
    - Last bin: values > last bound go to the last bin

    Args:
        ws_expr: Polars expression for wind speed column
        wind_speed_bins: List of bin upper bounds (e.g., [1.0, 2.0, ..., 28.0])

    Returns:
        Polars expression that evaluates to bin index (0-indexed)

    Example:
        >>> ws_expr = pl.col("wind_speed")
        >>> bins = [1.0, 2.0, 3.0]
        >>> bin_expr = _create_wind_speed_bin_expr(ws_expr, bins)
        >>> df.with_columns(bin_expr.alias("bin"))
    """
    # Start with default invalid value
    bin_expr: pl.Expr = pl.lit(-1)
    prev_bound = 0.0

    # Build when/then chain for each bin
    for i, bound in enumerate(wind_speed_bins):
        bin_expr = pl.when(
            (ws_expr > prev_bound) & (ws_expr <= bound)
        ).then(pl.lit(i)).otherwise(bin_expr)
        prev_bound = bound

    # Handle values > last bin bound - assign to last bin
    bin_expr = pl.when(ws_expr > prev_bound).then(
        pl.lit(len(wind_speed_bins) - 1)
    ).otherwise(bin_expr)

    return bin_expr


def calculate_ti_matrix(
    df: pl.DataFrame,
    ws_col: str,
    sd_col: str,
    wd_col: str,
    wind_speed_bins: list[float],
) -> dy.DataFrame[TIMatrixSchema]:
    """Calculate TI matrix from raw wind data.

    Creates a matrix with wind speed bins as rows and 16 direction sectors
    as columns. Each cell contains the mean TI for that bin/sector combination.

    TI is calculated as:
        TI = WS_sd / max(WS_avg, 1.0)

    Cells with fewer than 5 samples use the overall mean TI as fallback.

    Args:
        df: Input DataFrame with wind speed, SD, and direction columns
        ws_col: Column name for wind speed (average)
        sd_col: Column name for wind speed standard deviation
        wd_col: Column name for wind direction
        wind_speed_bins: List of wind speed bin upper bounds (e.g., [1.0, 2.0, ..., 28.0])

    Returns:
        ValidatedFrame with TIMatrixSchema containing columns:
        - v_max: Wind speed bin upper bound
        - N, NNE, NE, ..., NNW: Mean TI values for 16 sectors (0-1 range)

        Missing values are filled with mean_ti. The matrix has shape (n_bins, 17).

    Example:
        >>> ti_matrix = calculate_ti_matrix(df, "ws", "ws_sd", "wd", list(range(1, 29)))
        >>> print(ti_matrix.shape)
        (28, 17)
    """
    # Build expressions
    ws_expr = pl.col(ws_col)
    sd_expr = pl.col(sd_col)
    wd_expr = pl.col(wd_col)

    # Calculate TI and sector
    ti_expr = (sd_expr / pl.max_horizontal(ws_expr, pl.lit(1.0))).clip(upper_bound=1.0)
    sector_expr = _direction_to_sector(wd_expr)

    # Create bin index expression
    bin_expr = _create_wind_speed_bin_expr(ws_expr, wind_speed_bins)

    # Filter valid data and add calculated columns
    working_df = df.filter(
        ws_expr.is_not_null() & sd_expr.is_not_null() & wd_expr.is_not_null()
    ).with_columns([
        ti_expr.alias("ti"),
        sector_expr.alias("sector"),
        bin_expr.alias("wind_bin"),
    ])

    if working_df.is_empty():
        # Fallback to 0.1 TI for all wind bins and sectors when no data available
        data: dict[str, list] = {"v_max": wind_speed_bins}
        for sector_name in DIRECTION_16_SECTORS:
            data[sector_name] = [0.1] * len(wind_speed_bins)
        return TIMatrixSchema.validate(pl.DataFrame(data), cast=True)

    # Calculate overall mean TI for fallback
    mean_ti = working_df.select(pl.col("ti").mean()).item()
    if mean_ti is None or (isinstance(mean_ti, float) and mean_ti != mean_ti):
        mean_ti = 0.1
    else:
        mean_ti = float(mean_ti)

    # Group by wind_bin and sector, calculate mean TI and count
    agg_df = working_df.group_by(["wind_bin", "sector"]).agg([
        pl.col("ti").mean().alias("ti_mean"),
        pl.col("ti").count().alias("count"),
    ])

    # Filter out cells with fewer than 5 samples - these will use fallback
    valid_agg_df = agg_df.filter(pl.col("count") >= 5)

    # Cast sector to string so pivot creates string column names
    valid_agg_df = valid_agg_df.with_columns(pl.col("sector").cast(pl.String))

    # Use pivot to transform from long to wide format
    pivoted_df = valid_agg_df.pivot(
        values="ti_mean",
        index="wind_bin",
        on="sector",
        aggregate_function="first"
    )

    # Create a base DataFrame with all bins and their v_max values
    base_df = pl.DataFrame({
        "wind_bin": list(range(len(wind_speed_bins))),
        "v_max": wind_speed_bins,
    })

    # Join with pivoted data to ensure all bins are present
    result_df = base_df.join(pivoted_df, on="wind_bin", how="left")

    # Rename sector columns from indices (0-15) to names (N, NNE, etc.)
    # Use a lambda to handle both integer and string column names from pivot
    def rename_sector_column(col_name: str) -> str:
        try:
            idx = int(col_name)
            if 0 <= idx < 16:
                return DIRECTION_16_SECTORS[idx]
        except ValueError:
            pass
        return col_name

    result_df = result_df.rename(rename_sector_column)

    # Drop wind_bin column
    result_df = result_df.drop("wind_bin")

    # Ensure all sector columns exist (add missing ones with mean_ti values)
    for sector_name in DIRECTION_16_SECTORS:
        if sector_name not in result_df.columns:
            result_df = result_df.with_columns(pl.lit(mean_ti).alias(sector_name))

    # Reorder columns and fill any remaining nulls with mean_ti
    result_df = result_df.select(["v_max"] + DIRECTION_16_SECTORS)
    result_df = result_df.fill_null(mean_ti)

    return TIMatrixSchema.validate(result_df, cast=True)


def save_meteodyn_ti(
    output_dir: str,
    ti_matrix: pl.DataFrame,
    height: float,
) -> None:
    """Save TI matrix to MeteoDyn format file.

    Format:
    Line 1: row_count (number of wind speed bins, typically 28)
    Lines 2+: v_max + 16 sector values (tab-separated)

    Args:
        output_dir: Directory path for output file
        ti_matrix: TI matrix DataFrame with v_max + 16 sector columns
        height: Height in meters (used in filename)

    Raises:
        ValueError: If ti_matrix doesn't have expected columns

    Example:
        >>> save_meteodyn_ti("./output", ti_matrix, 100.0)
        # Creates: ./output/meteodyn_ti_100m.txt
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Validate columns
    expected_sectors = set(DIRECTION_16_SECTORS)
    actual_columns = set(ti_matrix.columns)
    if not expected_sectors.issubset(actual_columns):
        missing = expected_sectors - actual_columns
        raise ValueError(f"TI matrix missing sector columns: {missing}")

    if "v_max" not in actual_columns:
        raise ValueError("TI matrix missing 'v_max' column")

    # Build output lines
    n_rows = len(ti_matrix)
    lines: list[str] = [str(n_rows)]

    # Build column order: v_max first, then sectors in order
    columns_order = ["v_max"] + DIRECTION_16_SECTORS

    for row in ti_matrix.iter_rows(named=True):
        values = [str(row[col]) for col in columns_order]
        lines.append("\t".join(values))

    # Write file
    output_file = output_path / f"meteodyn_ti_{int(height)}m.txt"
    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    logger.info(f"Saved TI matrix for {height}m to {output_file}")


def load_meteodyn_ti(file_path: str) -> pl.DataFrame:
    """Load TI matrix from MeteoDyn format file.

    Reads a MeteoDyn TI file and returns a DataFrame with the matrix data.

    Args:
        file_path: Path to the MeteoDyn TI file

    Returns:
        DataFrame with v_max + 16 sector columns

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid

    Example:
        >>> ti_matrix = load_meteodyn_ti("./meteodyn_ti_100m.txt")
        >>> print(ti_matrix.columns)
        ['v_max', 'N', 'NNE', 'NE', ... 'NNW']
    """
    file = Path(file_path)
    if not file.exists():
        raise FileNotFoundError(f"TI file not found: {file_path}")

    content = file.read_text(encoding="utf-8").strip()
    lines = content.split("\n")

    if len(lines) < 2:
        raise ValueError(f"Invalid TI file format: {file_path}")

    # Parse row count
    try:
        n_rows = int(lines[0].strip())
    except ValueError as e:
        raise ValueError(f"Invalid row count in TI file: {lines[0]}") from e

    data_rows = lines[1:]
    if len(data_rows) != n_rows:
        raise ValueError(
            f"Row count mismatch: expected {n_rows}, got {len(data_rows)}"
        )

    # Parse data rows
    data: dict[str, list] = {"v_max": []}
    for sector in DIRECTION_16_SECTORS:
        data[sector] = []

    for line in data_rows:
        values = line.strip().split("\t")
        if len(values) != 17:  # v_max + 16 sectors
            raise ValueError(f"Invalid row format (expected 17 columns): {line}")

        data["v_max"].append(float(values[0]))
        for i, sector in enumerate(DIRECTION_16_SECTORS, start=1):
            data[sector].append(float(values[i]))

    return pl.DataFrame(data)


def _find_nearest_sensor(
    sensors: list[SensorColumn],
    target_height: float,
    sensor_type: str,
    stat_type: str,
) -> SensorColumn | None:
    """Find the sensor closest to the target height.

    Args:
        sensors: List of available sensors
        target_height: Target height in meters
        sensor_type: Sensor type to filter by (e.g., "WindSpeed")
        stat_type: Statistic type to filter by (e.g., "avg")

    Returns:
        Closest matching sensor or None if no match found
    """
    matching_sensors = [
        s
        for s in sensors
        if s.sensor_type == sensor_type and s.stat_type == stat_type
    ]

    if not matching_sensors:
        return None

    return min(matching_sensors, key=lambda s: abs(s.height - target_height))


def _find_wind_speed_sd_sensor(
    sensors: list[SensorColumn],
    target_height: float,
) -> SensorColumn | None:
    """Find the WindSpeed SD sensor closest to the target height.

    Args:
        sensors: List of available sensors
        target_height: Target height in meters

    Returns:
        Closest WindSpeed SD sensor or None if no match found
    """
    return _find_nearest_sensor(sensors, target_height, "WindSpeed", "sd")


def process_turbulence_for_height(
    ts_data: pl.DataFrame,
    target_height: float,
    sensors: list[SensorColumn],
) -> pl.DataFrame:
    """Calculate TI matrix for a specific height.

    Finds the appropriate sensors for the target height:
    - WindSpeed avg (same height)
    - WindSpeed sd (same height)
    - WindDirection avg (nearest available)

    Then calculates the TI matrix and returns it.

    Args:
        ts_data: Input time series DataFrame
        target_height: Target height for TI calculation
        sensors: List of available sensors

    Returns:
        TI matrix DataFrame with v_max + 16 sector columns

    Raises:
        ValueError: If required sensors are not found
    """
    # Find sensors
    ws_sensor = _find_nearest_sensor(sensors, target_height, "WindSpeed", "avg")
    if ws_sensor is None:
        raise ValueError(
            f"No WindSpeed avg sensor found for height {target_height}m"
        )

    sd_sensor = _find_wind_speed_sd_sensor(sensors, target_height)
    if sd_sensor is None:
        raise ValueError(
            f"No WindSpeed sd sensor found for height {target_height}m"
        )

    wd_sensor = _find_nearest_sensor(sensors, target_height, "WindDirection", "avg")
    if wd_sensor is None:
        raise ValueError(
            f"No WindDirection avg sensor found for height {target_height}m"
        )

    # Generate wind speed bins: 1.0, 2.0, ..., 28.0
    wind_speed_bins = [float(i) for i in range(1, 29)]

    # Calculate TI matrix
    ti_matrix = calculate_ti_matrix(
        ts_data,
        ws_sensor.column_name,
        sd_sensor.column_name,
        wd_sensor.column_name,
        wind_speed_bins,
    )

    return ti_matrix


def process_turbulence_for_mast(
    mast: WtTimeSeriesMast,
    project_dir: Path,
) -> None:
    """Process all turbulence heights for a mast.

    For each turbulence_height in the mast configuration:
    - Calculates the TI matrix
    - Saves to ./wt-timeseries/turbulence-{mast_name}/meteodyn_ti_{height}m.txt

    Args:
        mast: WtTimeSeriesMast configuration
        project_dir: Project directory for input/output path resolution

    Example:
        >>> mast = WtTimeSeriesMast(
        ...     name="TGL1",
        ...     input=TimeSeriesSource(data="./data.parquet"),
        ...     csv_heights=[100.0, 120.0],
        ...     turbulence_heights=[80.0, 100.0],
        ... )
        >>> process_turbulence_for_mast(mast, Path("./my-project"))
    """
    # Load data
    repo = ParquetRepository()
    ts_data_result = repo.load(mast.input, str(project_dir))
    df = ts_data_result.df
    sensors = ts_data_result.sensors

    # Create output directory
    output_dir = project_dir / "wt-timeseries" / f"turbulence-{mast.name}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each turbulence height
    for height in mast.turbulence_heights:
        try:
            ti_matrix = process_turbulence_for_height(df, height, sensors)
            save_meteodyn_ti(str(output_dir), ti_matrix, height)
        except ValueError as e:
            logger.warning(
                f"Mast '{mast.name}': Could not process turbulence for {height}m: {e}"
            )
            continue

    logger.info(
        f"Mast '{mast.name}': Processed turbulence for "
        f"{len(mast.turbulence_heights)} height(s)"
    )
