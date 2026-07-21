"""Train fill-height models use case.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-a-001-use-case-pattern
Compliance: Subdomain layout ✓ | Use Case ✓ | CLI Adapter Ready ✓

Trains fill-height models (shear / deg_diff) from reconstruct-meso data and
persists one TOML per mast x strategy x variable under
``fill-models/{mast}/{strategy}/{variable}-fit.toml``.

The application layer orchestrates across subdomains: discovery and
persistence live in ``configuration`` (ProjectConfig), fitting lives in
``dataprocessing`` (planner.fit_all_masts).  Neither subdomain imports the
other.
"""

from cleanmast.shared.timeseries import MastPlanningEntry
from cleanmast.subdomains.configuration import ProjectConfig
from cleanmast.subdomains.configuration.model.fill_height_fit_result import (
    FillHeightFitResult,
)
from cleanmast.subdomains.dataprocessing.services.height_filling.helpers import (
    get_top_sensors,
)
from cleanmast.subdomains.dataprocessing.services.height_filling.planner import (
    fit_all_masts,
)

# Strategy identifier for models trained from reconstruct-meso data with the
# top layer removed.  Future strategies get sibling directories at
# fill-models/{mast}/{strategy}/.
REMOVE_TOP_LAYER_STRATEGY: str = "remove-top-layer"


def train_fill_heights(
    project_config: ProjectConfig,
    heights: str,
    deg_diff_limit: float,
) -> None:
    """Train fill-height models for all masts in a project.

    1. Discover ``reconstruct-meso.toml`` via ProjectConfig (required).
    2. Fit shear (WS) and deg_diff (WD) per mast via ``fit_all_masts``.
    3. Persist one ``FillHeightFitResult`` per variable under
       ``fill-models/{mast}/remove-top-layer/{ws,wd}-fit.toml``.

    Args:
        project_config: ProjectConfig instance for the project directory.
        heights: Comma-separated target heights in meters (informational;
            the fit itself is height-agnostic).
        deg_diff_limit: Maximum absolute value for deg_diff_per_m in deg/m.

    Raises:
        FileNotFoundError: If reconstruct-meso.toml not found.
    """
    project_path = project_config.project_dir

    target_heights = [float(h.strip()) for h in heights.split(",")]
    print(f"Training fill-height models (target heights: {target_heights} m)")

    # Discover reconstruct-meso config (required)
    reconstruct_meso_dc = project_config.discover_reconstruct_meso_config()
    if reconstruct_meso_dc is None:
        raise FileNotFoundError(
            f"reconstruct-meso.toml not found at {project_path}. "
            "Run this command after reconstruct-meso step."
        )
    reconstruct_config = reconstruct_meso_dc.config

    # Build planning entries and fit all masts
    mast_entries = [
        MastPlanningEntry(name=m.name, output=m.output)
        for m in reconstruct_config.masts
    ]
    fitted = fit_all_masts(mast_entries, str(project_path), deg_diff_limit)

    # Serialize one model per mast x strategy x variable
    for mast_name, fit_data in fitted.items():
        timeseries = fit_data["timeseries"]

        ws_top = get_top_sensors(timeseries, "WindSpeed", n=1)
        ws_refs = get_top_sensors(timeseries, "WindSpeed", n=3)
        ws_result = FillHeightFitResult(
            strategy=REMOVE_TOP_LAYER_STRATEGY,
            target_type="WindSpeed",
            removed_height=max(s.height for s in ws_top),
            reference_heights=sorted(s.height for s in ws_refs),
            shear=fit_data["ws_shear_top3"],
        )
        ws_path = project_config.save_fill_height_model(
            ws_result, mast_name, REMOVE_TOP_LAYER_STRATEGY, "ws"
        )

        wd_top = get_top_sensors(timeseries, "WindDirection", n=1)
        wd_refs = get_top_sensors(timeseries, "WindDirection", n=3)
        wd_result = FillHeightFitResult(
            strategy=REMOVE_TOP_LAYER_STRATEGY,
            target_type="WindDirection",
            removed_height=max(s.height for s in wd_top),
            reference_heights=sorted(s.height for s in wd_refs),
            deg_diff_per_m=fit_data["wd_deg_diff_top3"],
        )
        wd_path = project_config.save_fill_height_model(
            wd_result, mast_name, REMOVE_TOP_LAYER_STRATEGY, "wd"
        )

        print(
            f"{mast_name}: strategy={REMOVE_TOP_LAYER_STRATEGY} "
            f"ws.shear={ws_result.shear:.6f} -> {ws_path}"
        )
        print(
            f"{mast_name}: strategy={REMOVE_TOP_LAYER_STRATEGY} "
            f"wd.deg_diff_per_m={wd_result.deg_diff_per_m:.6f} -> {wd_path}"
        )
