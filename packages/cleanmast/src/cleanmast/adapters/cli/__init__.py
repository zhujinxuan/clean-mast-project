"""CLI adapters.

ADR-GUARDRAILS: cli-001-comonicon-cli, structure-001-subdomain-layout
"""

from .recommend_fill_heights import recommend_fill_heights
from .execute_fill_heights import execute_fill_heights
from .recommend_report import recommend_rep_ts_report
from .generate_report import report_rep_ts
from .recommend_wt_timeseries import recommend_wt_timeseries_cli
from .generate_wt_timeseries import execute_wt_timeseries_cli

__all__ = [
    "recommend_fill_heights",
    "execute_fill_heights",
    "recommend_rep_ts_report",
    "report_rep_ts",
    "recommend_wt_timeseries_cli",
    "execute_wt_timeseries_cli",
]
