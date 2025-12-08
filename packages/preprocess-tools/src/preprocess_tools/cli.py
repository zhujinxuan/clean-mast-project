"""Unified CLI for preprocess-tools."""

import click

from .csv_merger import main as csv_merger_main
from .col_name_normalizer import main as col_normalizer_main
from .type_normalizer import main as type_normalizer_main
from .timestamp_normalizer import main as timestamp_normalizer_main


@click.group()
@click.version_option(version="0.1.0")
def main():
    """
    Preprocess Tools - Generic CSV preprocessing utilities for wind measurement data.

    Tools for preprocessing raw mast/lidar data files:
    - csv-merge: Merge multiple CSV files with timestamp normalization
    - col-normalizer: Normalize column names to standard formats (NRG, Lidar)
    - type-normalizer: Convert string columns to numeric types
    - timestamp: Normalize timestamp formats
    """
    pass


# Register subcommands
main.add_command(csv_merger_main, name="csv-merge")
main.add_command(col_normalizer_main, name="col-normalizer")
main.add_command(type_normalizer_main, name="type-normalizer")
main.add_command(timestamp_normalizer_main, name="timestamp")


if __name__ == "__main__":
    main()
