"""CleanMast CLI entry point."""

import shutil
from pathlib import Path

import click

from .adapters.cli import (
    execute_fill_heights,
    execute_wt_timeseries_cli,
    recommend_fill_heights,
    recommend_timeseries_report,
    recommend_wt_timeseries_cli,
    report_timeseries,
    train_fill_heights,
    verify,
)


@click.group()
@click.version_option(version="0.1.0")
def main():
    """CleanMast - Wind energy meteorological tower data analysis toolkit."""
    pass


@main.command()
@click.argument("project_dir", type=click.Path())
def init(project_dir: str):
    """Initialize a new project with template structure."""
    project_path = Path(project_dir)

    if not project_path.exists():
        project_path.mkdir(parents=True)
        click.echo(f"Created project directory: {project_path}")
    else:
        click.echo(f"Project directory exists: {project_path}")

    scaffold_dir = Path(__file__).parent / "scaffold"

    for item in scaffold_dir.iterdir():
        if item.name == "__pycache__":
            continue
        target = project_path / item.name
        if not target.exists():
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
            click.echo(f"Created: {target}")
        else:
            click.echo(f"Exists: {target}")

    click.echo(f"\nProject initialized at: {project_path}")


# === Recommend command group ===


@main.group()
def recommend():
    """Generate configuration files for various processing steps."""
    pass


# Register fill-heights commands
recommend.add_command(recommend_fill_heights, "fill-heights")
main.add_command(execute_fill_heights, "fill-heights")

# Register wt-timeseries commands
recommend.add_command(recommend_wt_timeseries_cli, "wt-timeseries")
main.add_command(execute_wt_timeseries_cli, "wt-timeseries")

# === Train command group ===


@main.group()
def train():
    """Train models for data processing."""
    pass


train.add_command(train_fill_heights, "fill-heights")

# === Report command group ===


@main.group()
def report():
    """Generate reports from processed data."""
    pass


# Register report generation commands
report.add_command(report_timeseries, "timeseries")

# Register verify command
main.add_command(verify, "verify")

# === Recommend report subgroup ===


@recommend.group()
def report_configs():
    """Generate report configurations."""
    pass


report_configs.add_command(recommend_timeseries_report, "timeseries")


# === Process command group ===


@main.group()
def process():
    """Execute data processing pipeline steps."""
    pass


@process.command()
@click.option("--config", required=True, type=click.Path(exists=True))
def reconstruct_single(config: str):
    """Reconstruct data using single-mast correlation."""
    raise NotImplementedError(
        "Single-mast reconstruction is not yet implemented in Python. "
        "Use: julia bin/CleanMast.jl reconstruct-single"
    )


@process.command()
@click.option("--config", required=True, type=click.Path(exists=True))
def reconstruct_meso(config: str):
    """Reconstruct data using mesoscale correlation."""
    raise NotImplementedError(
        "Mesoscale reconstruction is not yet implemented in Python. "
        "Use: julia bin/CleanMast.jl reconstruct-meso"
    )


# === Recommend clean command ===


@recommend.command()
@click.option("--output", "-o", default="clean-config.toml", help="Output config file path")
@click.argument("project_dir", type=click.Path(exists=True))
def clean(project_dir: str, output: str):
    """Generate configuration for data cleaning step."""
    raise NotImplementedError(
        "Data cleaning configuration is not yet implemented in Python. "
        "Use: julia bin/CleanMast.jl recommend process-clean"
    )


if __name__ == "__main__":
    main()
