"""Recommend fill-heights use case.

Description: Application use case for generating fill-heights configuration files

This module provides the use case for generating fill-heights configuration
files based on reconstruct-meso data.  It orchestrates across subdomains:
discovery lives in ``configuration`` (ProjectConfig), planning lives in
``dataprocessing`` (planner.generate_dual_configs).  Neither subdomain
imports the other.
"""

from cleanmast.infrastructure.path_utils import to_posix_path
from cleanmast.shared.timeseries import MastPlanningEntry
from cleanmast.subdomains.configuration import (
    DiscoveredConfig,
    FillHeightsMesoConfiguration,
    FillHeightsRepYearConfiguration,
    ProjectConfig,
)
from cleanmast.subdomains.dataprocessing.services.height_filling.planner import (
    generate_dual_configs,
)

# Default deg_diff_per_m limit (22.5° over 20m = 1.125 deg/m)
DEFAULT_DEG_DIFF_PER_M_LIMIT: float = 22.5 / 20  # 1.125 deg/m

# Default target heights for fill-heights
DEFAULT_FILL_HEIGHTS: str = "125,140,160"


def recommend_fill_heights(
    project_config: ProjectConfig,
    heights: str = DEFAULT_FILL_HEIGHTS,
    deg_diff_limit: float = DEFAULT_DEG_DIFF_PER_M_LIMIT,
) -> tuple[DiscoveredConfig[FillHeightsMesoConfiguration], DiscoveredConfig[FillHeightsRepYearConfiguration] | None]:
    """Generate fill-heights configuration files.

    This use case:
    1. Discovers reconstruct-meso.toml via ProjectConfig
    2. Loads the reconstructed timeseries data
    3. Fits shear and deg_diff parameters from top 3 layers
    4. Generates fill-heights configuration for each target height
    5. Creates dual configs (reconstruct-meso + representative-year if available)

    Prerequisites:
    - reconstruct-meso.toml must exist in project directory
    - reconstruct-meso processing must have been completed

    Args:
        project_config: ProjectConfig instance for the project directory
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

    # Generate dual configs
    meso_config, rep_config = generate_dual_configs(
        meso_masts=meso_entries,
        rep_year_masts=rep_entries,
        target_heights=target_heights,
        base_dir=to_posix_path(project_path),
        deg_diff_limit=deg_diff_limit,
    )

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
