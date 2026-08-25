"""CleanMast CLI entry point — groups and registration only.

CLI modules import from cleanmast.bootstrap only; never from
cleanmast.application.usecases or cleanmast.subdomains directly.
"""

import click

from .execute import execute_fill_heights, execute_wt_timeseries_cli
from .init import init
from .process import reconstruct_meso, reconstruct_single
from .recommend import (
    clean,
    recommend_fill_heights,
    recommend_timeseries_report,
    recommend_wt_timeseries_cli,
)
from .report import report_timeseries
from .train import train_fill_heights


@click.group()
@click.version_option(version="0.1.0")
def main():
    """CleanMast - Wind energy meteorological tower data analysis toolkit."""
    pass


@main.group()
def recommend():
    """Generate configuration files for various processing steps."""
    pass


@main.group()
def train():
    """Train models for data processing."""
    pass


@main.group()
def report():
    """Generate reports from processed data."""
    pass


@recommend.group()
def report_configs():
    """Generate report configurations."""
    pass


@main.group()
def process():
    """Execute data processing pipeline steps."""
    pass


# Register commands
main.add_command(init)
recommend.add_command(recommend_fill_heights, "fill-heights")
recommend.add_command(recommend_wt_timeseries_cli, "wt-timeseries")
recommend.add_command(clean)
report_configs.add_command(recommend_timeseries_report, "timeseries")
main.add_command(execute_fill_heights, "fill-heights")
main.add_command(execute_wt_timeseries_cli, "wt-timeseries")
train.add_command(train_fill_heights, "fill-heights")
report.add_command(report_timeseries, "timeseries")
process.add_command(reconstruct_single)
process.add_command(reconstruct_meso)
