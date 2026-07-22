"""Recommend fill-heights use case.

Description: Application use case for generating fill-heights configuration files

This module provides the use case for generating fill-heights configuration
files based on reconstruct-meso data.  It orchestrates across subdomains:
discovery lives in ``configuration`` (ProjectConfig), planning lives in
``dataprocessing`` (planner.fit_one_mast / build_one_mast_config).  Neither
subdomain imports the other.  Timeseries loading goes through the injected
``TimeSeriesRepository`` protocol, one mast at a time.
"""

from cleanmast.infrastructure.path_utils import to_posix_path
from cleanmast.shared.timeseries import MastPlanningEntry
from cleanmast.shared.timeseries.io import TimeSeriesRepository
from cleanmast.subdomains.configuration import (
    DiscoveredConfig,
    FillHeightsMesoConfiguration,
    FillHeightsRepYearConfiguration,
    ProjectConfig,
)
from cleanmast.subdomains.dataprocessing.services.height_filling.planner import (
    FitResult,
    build_one_mast_config,
    fit_one_mast,
    generate_dual_configs,
)

# Default deg_diff_per_m limit (22.5° over 20m = 1.125 deg/m)
DEFAULT_DEG_DIFF_PER_M_LIMIT: float = 22.5 / 20  # 1.125 deg/m

# Default target heights for fill-heights
DEFAULT_FILL_HEIGHTS: str = "125,140,160"


def recommend_fill_heights(
    project_config: ProjectConfig,
    repo: TimeSeriesRepository,
    heights: str = DEFAULT_FILL_HEIGHTS,
    deg_diff_limit: float = DEFAULT_DEG_DIFF_PER_M_LIMIT,
) -> tuple[DiscoveredConfig[FillHeightsMesoConfiguration], DiscoveredConfig[FillHeightsRepYearConfiguration] | None]:
    """Generate fill-heights configuration files.

    This use case:
    1. Discovers reconstruct-meso.toml via ProjectConfig
    2. Loads each mast's reconstructed timeseries via the injected repository
    3. Fits shear and deg_diff parameters from top 3 layers (one mast at a time)
    4. Generates fill-heights configuration for each target height
    5. Creates dual configs (reconstruct-meso + representative-year if available)

    Prerequisites:
    - reconstruct-meso.toml must exist in project directory
    - reconstruct-meso processing must have been completed

    Args:
        project_config: ProjectConfig instance for the project directory
        repo: TimeSeriesRepository used to load mast timeseries
        heights: Comma-separated target heights in meters
        deg_diff_limit: Maximum absolute value for deg_diff_per_m in deg/m

    Returns:
        Tuple of (meso_config, rep_year_config_or_none) as DiscoveredConfig wrappers

    Raises:
        FileNotFoundError: If reconstruct-meso.toml not found
        ValueError: If configuration is invalid
    """
    project_path = project_config.project_dir

    # Parse heights
    target_heights = [float(h.strip()) for h in heights.split(",")]

    # Discover reconstruct-meso config (required)
    reconstruct_meso_dc = project_config.discover_reconstruct_meso_config()
    if reconstruct_meso_dc is None:
        raise FileNotFoundError(
            f"reconstruct-meso.toml not found at {project_path}. "
            "Run this command after reconstruct-meso step."
        )
    reconstruct_config = reconstruct_meso_dc.config

    # Discover representative-year config (optional)
    rep_year_dc = project_config.discover_representative_year_config()
    rep_year_config = rep_year_dc.config if rep_year_dc else None

    # Build MastPlanningEntry lists from config objects
    meso_entries = [MastPlanningEntry(name=m.name, output=m.output) for m in reconstruct_config.masts]
    rep_entries = [MastPlanningEntry(name=m.name, output=m.output) for m in rep_year_config.masts] if rep_year_config else None

    base_dir = to_posix_path(project_path)

    # Fit parameters per mast — one load, one fit, one mast at a time.
    # Fit ONCE on reconstruct-meso data; the SAME FitResult feeds both streams.
    fitted: dict[str, FitResult] = {}
    for entry in meso_entries:
        timeseries = repo.load(entry.output, base_dir)
        fitted[entry.name] = fit_one_mast(timeseries, deg_diff_limit)

    # Build reconstruct-meso configs (reusing each mast's retained timeseries)
    meso_mast_configs = [
        build_one_mast_config(
            timeseries=fitted[entry.name].timeseries,
            fitted=fitted[entry.name],
            target_heights=target_heights,
            output_subdir="reconstruct-meso-fill-heights",
            name=entry.name,
            input_source=entry.output,
        )
        for entry in meso_entries
    ]

    # Build rep-year configs with the SAME fitted top3 params (if provided),
    # but neighbor fits computed from each rep-year timeseries itself —
    # mirroring the pre-DI behavior (one load per rep-year mast).
    rep_mast_configs = None
    if rep_entries:
        rep_mast_configs = []
        for entry in rep_entries:
            rep_timeseries = repo.load(entry.output, base_dir)
            rep_mast_configs.append(
                build_one_mast_config(
                    timeseries=rep_timeseries,
                    fitted=fitted[entry.name],
                    target_heights=target_heights,
                    output_subdir="representative-year-fill-heights",
                    name=entry.name,
                    input_source=entry.output,
                )
            )

    # Assemble dual configs
    meso_config, rep_config = generate_dual_configs(meso_mast_configs, rep_mast_configs)

    # Wrap in DiscoveredConfig — no file writing
    meso_dc: DiscoveredConfig[FillHeightsMesoConfiguration] = DiscoveredConfig(
        config=meso_config,
        filename="fill-heights-reconstruct-meso.toml",
    )

    rep_dc: DiscoveredConfig[FillHeightsRepYearConfiguration] | None = None
    if rep_config:
        rep_dc = DiscoveredConfig(
            config=rep_config,
            filename="fill-heights-representative-year.toml",
        )

    return meso_dc, rep_dc
