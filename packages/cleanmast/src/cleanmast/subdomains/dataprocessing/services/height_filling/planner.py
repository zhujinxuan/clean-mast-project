"""Fill heights planning service.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓
Description: Domain service for generating fill-heights configurations

This module implements the planning layer of the fill-heights system.
It orchestrates the generation of fill-heights configurations by:

1. Loading source data (reconstruct-meso output)
2. Fitting parameters (shear, deg_diff) from the data
3. Generating configurations for target heights
4. Creating dual configs for both reconstruct-meso and rep-year outputs

Dual-Config Generation Pattern:
================================

The key insight is that we fit parameters ONCE from reconstruct-meso data,
then use those SAME parameters for both output streams.

    reconstruct-meso.toml
            │
            ▼
    ┌───────────────────────┐
    │  Load timeseries data │
    └───────────────────────┘
            │
            ▼
    ┌───────────────────────┐
    │ Fit shear & deg_diff  │  ← FIT ONCE
    │ from top 3 layers     │
    └───────────────────────┘
            │
            ▼
    ┌───────────────────────┐
    │ Generate configs      │  ← USE TWICE
    │ (extrapolation +      │
    │  interpolation)       │
    └───────────────────────┘
            │
    ┌───────┴───────┐
    ▼               ▼
┌──────────────┐  ┌──────────────────────┐
│ fill-heights │  │ fill-heights-        │
│ -reconstruct │  │ representative-year  │
│ -meso.toml   │  │ .toml                │
└──────────────┘  └──────────────────────┘
        │                 │
        ▼                 ▼
  execute with       execute with
  meso data          rep-year data

Why Fit Once and Use Twice?
============================

1. Consistency: Both output streams use the same physical parameters
2. Efficiency: No need to re-fit from different data sources
3. Physical validity: Shear/deg_diff are properties of the site, not the data source
4. Traceability: Easy to see that both configs came from the same analysis

Strategy Selection Logic:
=========================

The planner automatically selects the appropriate strategy based on:
- Target height relative to existing heights
- Interpolation: target is between existing heights → use neighbors
- Extrapolation: target is above max existing → use top3 for fitting

Available Strategies:
- WSExtrapolateTop3Strategy: Extrapolate WS above highest sensor
- WSInterpolateInterStrategy: Interpolate WS between two sensors
- WDExtrapolateTop3Strategy: Extrapolate WD above highest sensor
- WDInterpolateInterStrategy: Interpolate WD between two sensors
"""


from cleanmast.subdomains.configuration.value_objects.fill_height_config import (
    FillHeightsConfiguration,
    MastFillConfig,
    WindDirectionHeightConfig,
    WindSpeedHeightConfig,
)
from cleanmast.subdomains.configuration.value_objects.reconstruct_meso import (
    ReconstructMesoConfiguration,
)
from cleanmast.subdomains.configuration.value_objects.representative_year import (
    RepresentativeYearConfiguration,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.infrastructure.timeseries_io import load_timeseries
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)

from .fitting import (
    fit_deg_diff_neighbors,
    fit_deg_diff_top3,
    fit_shear_neighbors,
    fit_shear_top3,
)
from .helpers import (
    create_fill_target_sensor,
    find_neighbor_sensors,
    get_existing_sensors,
    get_top_sensors,
)
from .strategies.wd_extrapolate_top3 import WDExtrapolateTop3Strategy
from .strategies.wd_interpolate_inter import WDInterpolateInterStrategy
from .strategies.ws_extrapolate_top3 import WSExtrapolateTop3Strategy
from .strategies.ws_interpolate_inter import WSInterpolateInterStrategy


def generate_dual_configs(
    reconstruct_meso_config: ReconstructMesoConfiguration,
    representative_year_config: RepresentativeYearConfiguration | None,
    target_heights: list[float],
    base_dir: str,
    deg_diff_limit: float = 1.125,
) -> tuple[FillHeightsConfiguration, FillHeightsConfiguration | None]:
    """Generate fill-heights configs for both reconstruct-meso and rep-year outputs.

    This is the main entry point for the planning layer. It orchestrates the
    complete workflow of fitting parameters and generating configurations.

    Workflow:
    1. Load reconstruct-meso data and fit shear/deg_diff parameters
    2. Generate config for reconstruct-meso output (using fitted params)
    3. Generate config for rep-year output (using SAME fitted params, if provided)

    Args:
        reconstruct_meso_config: Config with reconstruct-meso output paths.
            Contains mast configurations pointing to reconstructed data.
        representative_year_config: Optional rep-year config.
            If provided, generates a second config using the same fitted parameters.
        target_heights: Target heights to fill.
            Heights in meters where we want to generate wind speed/direction data.
        base_dir: Base directory for resolving relative paths.
            All paths in configs are relative to this directory.
        deg_diff_limit: Maximum absolute value for deg_diff_per_m in deg/m.
            Default is 1.125 deg/m (22.5° over 20m).

    Returns:
        Tuple of (meso_config, rep_year_config | None):
            - meso_config: FillHeightsConfiguration for reconstruct-meso output
            - rep_year_config: FillHeightsConfiguration for rep-year output, or None

    Raises:
        ValueError: If masts in configs don't match
        FileNotFoundError: If source data files don't exist

    Example:
        meso_config = ReconstructMesoConfiguration(...)
        rep_config = RepresentativeYearConfiguration(...)
        heights = [120.0, 140.0, 160.0]

        meso, rep = generate_dual_configs(meso_config, rep_config, heights, "/project")
        # meso → fill-heights-reconstruct-meso.toml
        # rep  → fill-heights-representative-year.toml
    """
    # Step 1: Load reconstruct-meso data and fit parameters
    # We fit ONCE on reconstruct-meso data
    fit_data = _load_and_fit(reconstruct_meso_config, base_dir, deg_diff_limit)

    # Step 2: Generate reconstruct-meso config
    meso_masts = _build_mast_configs(
        source_config=reconstruct_meso_config,
        target_heights=target_heights,
        fitted_params=fit_data,
        output_subdir="reconstruct-meso-fill-heights",
        base_dir=base_dir,
    )
    meso_output = FillHeightsConfiguration(
        strategy="default",
        masts=meso_masts,
    )

    # Step 3: Generate rep-year config (if provided)
    if representative_year_config:
        rep_masts = _build_mast_configs(
            source_config=representative_year_config,
            target_heights=target_heights,
            fitted_params=fit_data,  # SAME fitted params!
            output_subdir="representative-year-fill-heights",
            base_dir=base_dir,
        )
        rep_output = FillHeightsConfiguration(
            strategy="default",
            masts=rep_masts,
        )
        return meso_output, rep_output

    return meso_output, None


def _load_and_fit(
    reconstruct_meso_config: ReconstructMesoConfiguration,
    base_dir: str,
    deg_diff_limit: float = 1.125,
) -> dict:
    """Load reconstruct-meso data and fit shear/deg_diff for all masts.

    For each mast in the configuration:
    1. Load the reconstructed timeseries data
    2. Fit wind speed shear from top 3 layers
    3. Fit wind direction change from top 3 WD layers

    Args:
        reconstruct_meso_config: Configuration with mast definitions
        base_dir: Base directory for resolving paths
        deg_diff_limit: Maximum absolute value for deg_diff_per_m in deg/m.
            Default is 1.125 deg/m (22.5° over 20m).

    Returns:
        Dictionary mapping mast_name to fitted parameters:
        {
            "timeseries": TimeSeriesData,  # For reference height detection
            "ws_shear_top3": float,         # Shear from top 3 WS layers
            "wd_deg_diff_top3": float,      # deg_diff from top 3 WD layers
        }

    Example:
        fitted = _load_and_fit(config, "/project")
        # fitted["mast-01"]["ws_shear_top3"] -> 0.142
    """
    fitted = {}

    for mast in reconstruct_meso_config.masts:
        timeseries = load_timeseries(mast.output, base_dir)

        # Fit WS shear (top3 and we can use for neighbors too)
        ws_shear_top3 = fit_shear_top3(timeseries)

        # Fit WD deg_diff
        wd_deg_diff_top3 = fit_deg_diff_top3(timeseries, deg_diff_limit)

        fitted[mast.name] = {
            "timeseries": timeseries,
            "ws_shear_top3": ws_shear_top3,
            "wd_deg_diff_top3": wd_deg_diff_top3,
        }

    return fitted


def _build_mast_configs(
    source_config,  # ReconstructMesoConfiguration or RepresentativeYearConfiguration
    target_heights: list[float],
    fitted_params: dict,
    output_subdir: str,
    base_dir: str,
) -> list[MastFillConfig]:
    """Build mast configs for given source (reconstruct-meso or rep-year).

    This is a polymorphic function that works with both ReconstructMesoConfiguration
    and RepresentativeYearConfiguration. Both have the same structure for masts.

    Args:
        source_config: Either ReconstructMesoConfiguration or RepresentativeYearConfiguration
        target_heights: List of heights to generate fill configurations for
        fitted_params: Dictionary from _load_and_fit with fitted parameters
        output_subdir: Subdirectory for output files
        base_dir: Base directory for resolving paths

    Returns:
        List of MastFillConfig, one per mast in source_config
    """
    masts = []

    for mast in source_config.masts:
        # Get fitted data for this mast
        fit_data = fitted_params[mast.name]

        # Get existing heights from source timeseries
        source_timeseries = load_timeseries(mast.output, base_dir)

        # Build WS configs
        ws_configs = _build_ws_configs(
            source_timeseries=source_timeseries,
            target_heights=target_heights,
            fitted_shear_top3=fit_data["ws_shear_top3"],
        )

        # Build WD configs
        wd_configs = _build_wd_configs(
            source_timeseries=source_timeseries,
            target_heights=target_heights,
            fitted_deg_diff_top3=fit_data["wd_deg_diff_top3"],
        )

        # Create output paths
        output_data = f"./{output_subdir}/{mast.name}.parquet"
        output_sensors = f"./{output_subdir}/{mast.name}.sensors.yaml"

        masts.append(
            MastFillConfig(
                name=mast.name,
                input=mast.output,  # Use source output as input
                output=TimeSeriesSource(data=output_data, sensors=output_sensors),
                windspeed=ws_configs,
                winddirection=wd_configs,
            )
        )

    return masts


def _build_ws_configs(
    source_timeseries: TimeSeriesData,
    target_heights: list[float],
    fitted_shear_top3: float,
) -> list[WindSpeedHeightConfig]:
    """Build WS height configs using appropriate strategies.

    For each target height:
    1. Skip if height already exists
    2. Skip if below minimum existing height
    3. Use extrapolation if above max existing
    4. Use interpolation if between existing heights

    Args:
        source_timeseries: Timeseries with existing WS sensors
        target_heights: Heights to generate configs for
        fitted_shear_top3: Pre-fitted shear from top 3 layers

    Returns:
        List of WindSpeedHeightConfig for valid targets
    """
    configs = []
    existing = get_existing_sensors(source_timeseries.sensors, "WindSpeed")
    existing_heights = [s.height for s in existing]

    for target_height in target_heights:
        # Skip if exists
        if target_height in existing_heights:
            continue

        # Skip if below lowest
        if target_height < min(existing_heights):
            print(
                f"Warning: Skipping {target_height}m - below minimum sensor height {min(existing_heights)}m"
            )
            continue

        # Determine strategy and build config
        if target_height > max(existing_heights):
            # Extrapolation: Use top3 shear
            target = create_fill_target_sensor(
                source_timeseries, target_height, "WindSpeed", "extrapolated"
            )
            ref_sensors = get_top_sensors(source_timeseries, "WindSpeed", n=3)
            shear = fitted_shear_top3
            strategy = WSExtrapolateTop3Strategy()
            config = strategy.build_config(
                timeseries=source_timeseries,
                target=target,
                references=ref_sensors,
                shear=shear,
            )
        else:
            # Interpolation: Fit shear from neighbors
            target = create_fill_target_sensor(
                source_timeseries, target_height, "WindSpeed", "interpolated"
            )
            lower_sensor, higher_sensor = find_neighbor_sensors(
                target_height, existing
            )
            ref_sensors = [lower_sensor, higher_sensor]
            local_shear = fit_shear_neighbors(
                source_timeseries, lower_sensor, higher_sensor
            )
            strategy = WSInterpolateInterStrategy()
            config = strategy.build_config(
                timeseries=source_timeseries,
                target=target,
                references=ref_sensors,
                shear=local_shear,
            )

        if config:
            configs.append(config)

    return configs


def _build_wd_configs(
    source_timeseries: TimeSeriesData,
    target_heights: list[float],
    fitted_deg_diff_top3: float,
) -> list[WindDirectionHeightConfig]:
    """Build WD height configs using appropriate strategies.

    Same logic as WS configs but for wind direction.

    Args:
        source_timeseries: Timeseries with existing WD sensors
        target_heights: Heights to generate configs for
        fitted_deg_diff_top3: Pre-fitted deg_diff from top 3 layers

    Returns:
        List of WindDirectionHeightConfig for valid targets
    """
    configs = []
    existing = get_existing_sensors(source_timeseries.sensors, "WindDirection")
    existing_heights = [s.height for s in existing]

    for target_height in target_heights:
        # Skip if exists
        if target_height in existing_heights:
            continue

        # Skip if below lowest
        if target_height < min(existing_heights):
            continue  # Already warned for WS

        # Determine strategy and build config
        if target_height > max(existing_heights):
            # Extrapolation: Use top3 deg_diff
            target = create_fill_target_sensor(
                source_timeseries, target_height, "WindDirection", "extrapolated"
            )
            ref_sensors = get_top_sensors(source_timeseries, "WindDirection", n=3)
            deg_diff = fitted_deg_diff_top3
            strategy = WDExtrapolateTop3Strategy()
            config = strategy.build_config(
                timeseries=source_timeseries,
                target=target,
                references=ref_sensors,
                deg_diff_per_m=deg_diff,
            )
        else:
            # Interpolation: Fit deg_diff from neighbors
            target = create_fill_target_sensor(
                source_timeseries, target_height, "WindDirection", "interpolated"
            )
            lower_sensor, higher_sensor = find_neighbor_sensors(
                target_height, existing
            )
            ref_sensors = [lower_sensor, higher_sensor]
            local_deg_diff = fit_deg_diff_neighbors(
                source_timeseries, lower_sensor, higher_sensor
            )
            strategy = WDInterpolateInterStrategy()
            config = strategy.build_config(
                timeseries=source_timeseries,
                target=target,
                references=ref_sensors,
                deg_diff_per_m=local_deg_diff,
            )

        if config:
            configs.append(config)

    return configs
