"""Generate WT TimeSeries use case.


This module provides the use case for executing wt-timeseries processing
from configuration file.
"""

from pathlib import Path

from cleanmast.shared.timeseries.io import TimeSeriesRepository
from cleanmast.shared.timeseries.wt_timeseries_config import (
    WtTimeSeriesConfiguration,
)
from cleanmast.subdomains.configuration import load_config
from cleanmast.subdomains.dataprocessing.services.turbulence_calculator import (
    process_turbulence_for_mast,
)
from cleanmast.subdomains.dataprocessing.services.wt_timeseries_generator import (
    process_single_mast_csv,
)


def generate_wt_timeseries(config_path: Path, repo: TimeSeriesRepository) -> None:
    """Execute wt-timeseries processing from config file.

    1. Load and validate wt-timeseries.toml
    2. For each mast:
       - Load timeseries once via the injected repository
       - Call process_single_mast_csv() from wt_timeseries_generator
       - Call process_turbulence_for_mast() from turbulence_calculator
    3. Print progress output

    Args:
        config_path: Path to wt-timeseries.toml configuration file
        repo: TimeSeriesRepository used to load mast timeseries

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is invalid
    """
    config = load_config(WtTimeSeriesConfiguration, config_path)
    project_dir = config_path.parent

    for mast in config.masts:
        # Load this mast's timeseries once; feed both generators
        ts_data = repo.load(mast.input, str(project_dir))

        # Generate CSV file
        process_single_mast_csv(mast, ts_data, project_dir)

        # Generate turbulence files
        if mast.turbulence_heights:
            process_turbulence_for_mast(mast, ts_data, project_dir)
