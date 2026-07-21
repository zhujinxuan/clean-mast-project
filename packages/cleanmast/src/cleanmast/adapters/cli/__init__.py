"""CLI adapters.

ADR-GUARDRAILS: cli-001-comonicon-cli, structure-001-subdomain-layout
"""

from .execute_fill_heights import execute_fill_heights
from .generate_report import report_timeseries
from .generate_wt_timeseries import execute_wt_timeseries_cli
from .recommend_fill_heights import recommend_fill_heights
from .recommend_report import recommend_timeseries_report
from .recommend_wt_timeseries import recommend_wt_timeseries_cli
from .train_fill_heights import train_fill_heights
from .verify import verify

__all__ = [
    "recommend_fill_heights",
    "execute_fill_heights",
    "recommend_timeseries_report",
    "report_timeseries",
    "recommend_wt_timeseries_cli",
    "execute_wt_timeseries_cli",
    "train_fill_heights",
    "verify",
]
