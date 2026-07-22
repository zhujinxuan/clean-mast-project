"""Fill heights planning service.

Description: Domain service for generating fill-heights configurations

This module implements the planning layer of the fill-heights system.
It generates fill-heights configurations by:

1. Fitting parameters (shear, deg_diff) from loaded timeseries data
2. Generating configurations for target heights
3. Creating dual configs for both reconstruct-meso and rep-year outputs

I/O lives outside this module: the application layer loads ``TimeSeriesData``
via the repository protocol and passes it in, one mast at a time.

Dual-Config Generation Pattern:
================================

The key insight is that we fit parameters ONCE from reconstruct-meso data,
then use those SAME parameters for both output streams.

    reconstruct-meso data
    (loaded by caller)
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


from dataclasses import dataclass

from cleanmast.shared.timeseries import (
    FillHeightsMesoConfiguration,
    FillHeightsRepYearConfiguration,
    MastFillConfig,
    TimeSeriesData,
    WindDirectionHeightConfig,
    WindSpeedHeightConfig,
)
from cleanmast.shared.timeseries.time_series_source import (
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
    meso_mast_configs: list[MastFillConfig],
    rep_year_mast_configs: list[MastFillConfig] | None = None,
) -> tuple[FillHeightsMesoConfiguration, FillHeightsRepYearConfiguration | None]:
    """Assemble dual fill-heights configurations from pre-built mast configs.

    Pure assembler: the caller (application layer) loads data, fits parameters
    via :func:`fit_one_mast`, and builds per-mast configs via
    :func:`build_one_mast_config`. Both output streams reuse the SAME fitted
    parameters — see module docstring for the fit-once/use-twice rationale.

    Args:
        meso_mast_configs: Pre-built MastFillConfig list for reconstruct-meso.
        rep_year_mast_configs: Optional pre-built list for representative-year.

    Returns:
        Tuple of (meso_config, rep_year_config | None).
    """
    meso_output = FillHeightsMesoConfiguration(
        strategy="default",
        masts=meso_mast_configs,
    )

    if rep_year_mast_configs:
        rep_output = FillHeightsRepYearConfiguration(
            strategy="default",
            masts=rep_year_mast_configs,
        )
        return meso_output, rep_output

    return meso_output, None


@dataclass
class FitResult:
    """Fitted fill-height parameters for one mast.

    Attributes:
        ws_shear_top3: Shear fitted from top 3 WS layers.
        wd_deg_diff_top3: deg_diff fitted from top 3 WD layers.
        timeseries: The source timeseries, retained for
            :func:`build_one_mast_config` (reference height detection).
    """

    ws_shear_top3: float
    wd_deg_diff_top3: float
    timeseries: TimeSeriesData


def fit_one_mast(
    timeseries: TimeSeriesData,
    deg_diff_limit: float = 1.125,
) -> FitResult:
    """Fit shear and deg_diff from one mast's timeseries.

    Args:
        timeseries: Loaded reconstruct-meso timeseries for one mast.
        deg_diff_limit: Maximum absolute value for deg_diff_per_m in deg/m.
            Default is 1.125 deg/m (22.5° over 20m).

    Returns:
        FitResult with fitted parameters and the source timeseries.
    """
    ws_shear_top3 = fit_shear_top3(timeseries)
    wd_deg_diff_top3 = fit_deg_diff_top3(timeseries, deg_diff_limit)
    return FitResult(
        ws_shear_top3=ws_shear_top3,
        wd_deg_diff_top3=wd_deg_diff_top3,
        timeseries=timeseries,
    )


def build_one_mast_config(
    timeseries: TimeSeriesData,
    fitted: FitResult,
    target_heights: list[float],
    output_subdir: str,
    name: str,
    input_source: TimeSeriesSource,
) -> MastFillConfig:
    """Build the fill-heights config for one mast.

    Args:
        timeseries: Source timeseries for reference-height detection.
        fitted: FitResult from :func:`fit_one_mast` for this mast.
        target_heights: Heights to generate fill configurations for.
        output_subdir: Subdirectory for output files.
        name: Mast name.
        input_source: TimeSeriesSource used as the config's input
            (the mast's own output for its stream — meso or rep-year).

    Returns:
        MastFillConfig for this mast.
    """
    # Build WS configs
    ws_configs = _build_ws_configs(
        source_timeseries=timeseries,
        target_heights=target_heights,
        fitted_shear_top3=fitted.ws_shear_top3,
    )

    # Build WD configs
    wd_configs = _build_wd_configs(
        source_timeseries=timeseries,
        target_heights=target_heights,
        fitted_deg_diff_top3=fitted.wd_deg_diff_top3,
    )

    # Create output paths
    output_data = f"./{output_subdir}/{name}.parquet"
    output_sensors = f"./{output_subdir}/{name}.sensors.yaml"

    return MastFillConfig(
        name=name,
        input=input_source,
        output=TimeSeriesSource(data=output_data, sensors=output_sensors),
        windspeed=ws_configs,
        winddirection=wd_configs,
    )


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
