"""DataProcessing subdomain.

ADR-GUARDRAILS: structure-001-subdomain-layout
Compliance: Subdomain layout ✓ | DataProcessing Domain ✓
"""

from cleanmast.subdomains.dataprocessing.services import (
    HeightFiller,
    apply_ws_fill,
    apply_wd_fill,
    TIMatrixSchema,
    calculate_ti_matrix,
    calculate_ti_series,
    process_turbulence_for_mast,
    process_single_mast_csv,
    process_wt_timeseries,
)
from cleanmast.subdomains.dataprocessing.commands import (
    recommend_wt_timeseries,
    recommend_wt_timeseries_cli,
    execute_wt_timeseries,
    execute_wt_timeseries_cli,
)

__all__ = [
    # Services
    "HeightFiller",
    "apply_ws_fill",
    "apply_wd_fill",
    "TIMatrixSchema",
    "calculate_ti_matrix",
    "calculate_ti_series",
    "process_turbulence_for_mast",
    "process_single_mast_csv",
    "process_wt_timeseries",
    # Commands
    "recommend_wt_timeseries",
    "recommend_wt_timeseries_cli",
    "execute_wt_timeseries",
    "execute_wt_timeseries_cli",
]
