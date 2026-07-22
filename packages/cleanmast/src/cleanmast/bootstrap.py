"""Composition root — single source of truth for dependency wiring.

Call chain:  interfaces/cli/* -> bootstrap.build_*() -> application.usecase(repo=...) -> domain(data)

Protocols consumed (injected into usecases):
  - TimeSeriesRepository (from shared/timeseries/io/repository.py)
    -> realized by infrastructure/file_repository.py (FileTimeSeriesRepository)

Factories:
  build_recommend_fill_heights   -> recommend_fill_heights(project_config, repo, ...)
  build_train_fill_heights       -> train_fill_heights(project_config, repo, ...)
  build_execute_fill_heights     -> execute_fill_heights(config_path, repo)
  build_generate_report          -> generate_report(config_path, repo)
  build_generate_wt_timeseries   -> generate_wt_timeseries(config_path, repo)
  build_recommend_report         -> recommend_report(project_config, repo)
  build_recommend_wt_timeseries  -> recommend_wt_timeseries(project_config, repo)

CLI modules import from this module only — never from
``cleanmast.application.usecases`` or ``cleanmast.subdomains`` directly.
"""

from pathlib import Path

from cleanmast.application.usecases.execute_fill_heights import execute_fill_heights
from cleanmast.application.usecases.generate_report import generate_report
from cleanmast.application.usecases.generate_wt_timeseries import (
    generate_wt_timeseries,
)
from cleanmast.application.usecases.recommend_fill_heights import (
    DEFAULT_DEG_DIFF_PER_M_LIMIT,
    DEFAULT_FILL_HEIGHTS,
    recommend_fill_heights,
)
from cleanmast.application.usecases.train_fill_heights import train_fill_heights
from cleanmast.infrastructure.file_repository import FileTimeSeriesRepository
from cleanmast.subdomains.configuration import ProjectConfig
from cleanmast.subdomains.configuration.services.recommend_report import (
    recommend_report,
)
from cleanmast.subdomains.configuration.services.recommend_wt_timeseries import (
    recommend_wt_timeseries,
)

__all__ = [
    "DEFAULT_DEG_DIFF_PER_M_LIMIT",
    "DEFAULT_FILL_HEIGHTS",
    "build_execute_fill_heights",
    "build_generate_report",
    "build_generate_wt_timeseries",
    "build_recommend_fill_heights",
    "build_recommend_report",
    "build_recommend_wt_timeseries",
    "build_train_fill_heights",
]

# FileTimeSeriesRepository is stateless — construct once, reuse everywhere.
_repo = FileTimeSeriesRepository()


def build_recommend_fill_heights(
    project_dir: str,
    heights: str = DEFAULT_FILL_HEIGHTS,
    deg_diff_limit: float = DEFAULT_DEG_DIFF_PER_M_LIMIT,
):
    """Wire repo + ProjectConfig into the recommend-fill-heights usecase."""
    project_config = ProjectConfig(Path(project_dir))
    return recommend_fill_heights(
        project_config=project_config,
        repo=_repo,
        heights=heights,
        deg_diff_limit=deg_diff_limit,
    )


def build_train_fill_heights(
    project_dir: str,
    heights: str = DEFAULT_FILL_HEIGHTS,
    deg_diff_limit: float = DEFAULT_DEG_DIFF_PER_M_LIMIT,
) -> None:
    """Wire repo + ProjectConfig into the train-fill-heights usecase."""
    project_config = ProjectConfig(Path(project_dir))
    train_fill_heights(
        project_config=project_config,
        repo=_repo,
        heights=heights,
        deg_diff_limit=deg_diff_limit,
    )


def build_execute_fill_heights(config_path: str) -> None:
    """Wire repo into the execute-fill-heights usecase."""
    execute_fill_heights(config_path, repo=_repo)


def build_generate_report(config_path: str):
    """Wire repo into the generate-report usecase."""
    return generate_report(config_path, repo=_repo)


def build_generate_wt_timeseries(config_path: str) -> None:
    """Wire repo into the generate-wt-timeseries usecase."""
    generate_wt_timeseries(Path(config_path), repo=_repo)


def build_recommend_report(project_dir: str):
    """Wire repo + ProjectConfig into the recommend-report service."""
    project_config = ProjectConfig(Path(project_dir))
    return recommend_report(project_config, repo=_repo)


def build_recommend_wt_timeseries(project_dir: str):
    """Wire repo + ProjectConfig into the recommend-wt-timeseries service."""
    project_config = ProjectConfig(Path(project_dir))
    return recommend_wt_timeseries(project_config, repo=_repo)
