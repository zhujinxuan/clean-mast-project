"""Compute helpers for the cleaning capability.

Pure polars/numpy math — no IO, no side effects.
"""

from cleanmast.subdomains.reporting.subdomains.cleaning.compute.correlation import (
    correlation_matrix,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.compute.coverage import (
    CoverageStats,
    count_valid_points,
    coverage_stats,
    expected_points,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.compute.regression import (
    RegressionResult,
    linear_regression,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.compute.scatter_pairs import (
    CrossMastResult,
    MesoResult,
    SameTowerResult,
    analyze_cross_mast,
    analyze_meso,
    analyze_same_tower,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.compute.sector_stats import (
    assign_sector,
    sector_ws_stats,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.compute.tower_shading import (
    OVERALL_ROW_LABEL,
    DualChannelHeight,
    find_avg_wind_direction_column,
    find_dual_channel_heights,
    overall_weighted_row,
    tower_shading_comparison_frame,
    tower_shading_sector_stats,
)

__all__ = [
    "CoverageStats",
    "CrossMastResult",
    "DualChannelHeight",
    "MesoResult",
    "OVERALL_ROW_LABEL",
    "RegressionResult",
    "SameTowerResult",
    "analyze_cross_mast",
    "analyze_meso",
    "analyze_same_tower",
    "assign_sector",
    "correlation_matrix",
    "coverage_stats",
    "count_valid_points",
    "expected_points",
    "find_avg_wind_direction_column",
    "find_dual_channel_heights",
    "linear_regression",
    "overall_weighted_row",
    "sector_ws_stats",
    "tower_shading_comparison_frame",
    "tower_shading_sector_stats",
]
