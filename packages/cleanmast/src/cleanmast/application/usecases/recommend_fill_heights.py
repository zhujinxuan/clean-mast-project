"""Recommend fill-heights use case.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-a-001-use-case-pattern
Compliance: Subdomain layout ✓ | Use Case ✓ | CLI Adapter Ready ✓
Description: Application use case for generating fill-heights configuration files

This module provides the use case for generating fill-heights configuration
files based on reconstruct-meso data.
"""

from pathlib import Path

import tomli
import tomli_w

from cleanmast.infrastructure.path_utils import to_posix_path
from cleanmast.subdomains.configuration import (
    ReconstructMesoConfiguration,
    RepresentativeYearConfiguration,
    load_representative_year_config,
)
from cleanmast.subdomains.dataprocessing.services.height_filling.planner import (
    generate_dual_configs,
)

# Default deg_diff_per_m limit (22.5° over 20m = 1.125 deg/m)
DEFAULT_DEG_DIFF_PER_M_LIMIT: float = 22.5 / 20  # 1.125 deg/m

# Default target heights for fill-heights
DEFAULT_FILL_HEIGHTS: str = "125,140,160"


def recommend_fill_heights(
    project_dir: str,
    heights: str = DEFAULT_FILL_HEIGHTS,
    deg_diff_limit: float = DEFAULT_DEG_DIFF_PER_M_LIMIT,
) -> tuple[Path, Path | None]:
    """Generate fill-heights configuration files.

    This use case:
    1. Reads reconstruct-meso.toml from the project directory
    2. Loads the reconstructed timeseries data
    3. Fits shear and deg_diff parameters from top 3 layers
    4. Generates fill-heights configuration for each target height
    5. Creates dual configs (reconstruct-meso + representative-year if available)

    Prerequisites:
    - reconstruct-meso.toml must exist in project directory
    - reconstruct-meso processing must have been completed

    Args:
        project_dir: Path to project directory containing config files
        heights: Comma-separated target heights in meters
        deg_diff_limit: Maximum absolute value for deg_diff_per_m in deg/m

    Returns:
        Tuple of (meso_config_path, rep_year_config_path_or_none)

    Raises:
        FileNotFoundError: If reconstruct-meso.toml not found
        ValueError: If configuration is invalid
    """
    project_path = Path(project_dir)

    # Parse heights
    target_heights = [float(h.strip()) for h in heights.split(",")]

    # Load reconstruct-meso.toml
    reconstruct_meso_path = project_path / "reconstruct-meso.toml"
    if not reconstruct_meso_path.exists():
        raise FileNotFoundError(
            f"reconstruct-meso.toml not found at {reconstruct_meso_path}. "
            "Run this command after reconstruct-meso step."
        )

    with open(reconstruct_meso_path, "rb") as f:
        reconstruct_data = tomli.load(f)
    reconstruct_config = ReconstructMesoConfiguration(**reconstruct_data)

    # Load representative-year.toml (optional)
    rep_year_config: RepresentativeYearConfiguration | None = None
    rep_year_path = project_path / "representative-year.toml"

    if rep_year_path.exists():
        rep_year_config = load_representative_year_config(to_posix_path(rep_year_path))

    # Generate dual configs
    meso_config, rep_config = generate_dual_configs(
        reconstruct_meso_config=reconstruct_config,
        representative_year_config=rep_year_config,
        target_heights=target_heights,
        base_dir=to_posix_path(project_path),
        deg_diff_limit=deg_diff_limit,
    )

    # Write fill-heights-reconstruct-meso.toml
    meso_output_path = project_path / "fill-heights-reconstruct-meso.toml"
    with open(meso_output_path, "wb") as f:
        tomli_w.dump(meso_config.model_dump(exclude_none=True), f)

    rep_output_path: Path | None = None

    # Write fill-heights-representative-year.toml (if rep year exists)
    if rep_config:
        rep_output_path = project_path / "fill-heights-representative-year.toml"
        with open(rep_output_path, "wb") as f:
            tomli_w.dump(rep_config.model_dump(exclude_none=True), f)

    return meso_output_path, rep_output_path
