"""Commands for wt_timeseries processing.

ADR-GUARDRAILS: structure-001-subdomain-layout, cli-001-click-cli-patterns
Compliance: Subdomain layout ✓ | CLI Pattern ✓ | Command Package ✓
"""

from cleanmast.subdomains.dataprocessing.commands.recommend import (
    recommend_wt_timeseries,
    recommend_wt_timeseries_cli,
)
from cleanmast.subdomains.dataprocessing.commands.execute import (
    execute_wt_timeseries,
    execute_wt_timeseries_cli,
)

__all__ = [
    "recommend_wt_timeseries",
    "recommend_wt_timeseries_cli",
    "execute_wt_timeseries",
    "execute_wt_timeseries_cli",
]
