"""DataProcessing subdomain.

ADR-GUARDRAILS: structure-001-subdomain-layout
Compliance: Subdomain layout ✓ | DataProcessing Domain ✓
"""

from cleanmast.subdomains.dataprocessing.commands import (
    execute_wt_timeseries,
    execute_wt_timeseries_cli,
    recommend_wt_timeseries,
    recommend_wt_timeseries_cli,
)
from cleanmast.subdomains.dataprocessing.services import (
    HeightFiller,
    TIMatrixSchema,
    apply_wd_fill,
    apply_ws_fill,
    calculate_ti_matrix,
    calculate_ti_series,
    process_single_mast_csv,
    process_turbulence_for_mast,
    process_wt_timeseries,
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
