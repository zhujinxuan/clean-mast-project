"""Height filling services.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
"""

from .planner import generate_dual_configs
from .validation import validate_references, build_sensor_column_map
from .fitting import (
    fit_shear_top3,
    fit_shear_neighbors,
    fit_deg_diff_top3,
    fit_deg_diff_neighbors,
)
from .helpers import (
    get_existing_sensors,
    get_top_sensors,
    find_neighbor_sensors,
    create_fill_target_sensor,
    generate_target_column,
    calculate_interpolation_weights,
)

__all__ = [
    "generate_dual_configs",
    "validate_references",
    "build_sensor_column_map",
    "fit_shear_top3",
    "fit_shear_neighbors",
    "fit_deg_diff_top3",
    "fit_deg_diff_neighbors",
    "get_existing_sensors",
    "get_top_sensors",
    "find_neighbor_sensors",
    "create_fill_target_sensor",
    "calculate_interpolation_weights",
]
