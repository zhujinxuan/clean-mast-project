"""CleanMast CLI entry point."""

import shutil
from pathlib import Path

import click
import tomli
import tomli_w

from .extrapolate import execute_extrapolation, get_strategy, list_strategies
from .extrapolate.config import load_extrapolate_config
from .models.reconstruct_meso import ReconstructMesoConfiguration
from .models.representative_year import (
    RepresentativeYearConfiguration,
    load_representative_year_config,
)


@click.group()
@click.version_option(version="0.1.0")
def main():
    """CleanMast - Wind energy meteorological tower data analysis toolkit."""
    pass


@main.command()
@click.argument("project_dir", type=click.Path())
def init(project_dir: str):
    """Initialize a new project with template structure.

    Creates project directory with formats/, pre-masts/, and mesos/ subdirectories.
    """
    project_path = Path(project_dir)

    # Create project directory if it doesn't exist
    if not project_path.exists():
        project_path.mkdir(parents=True)
        click.echo(f"Created project directory: {project_path}")
    else:
        click.echo(f"Project directory exists: {project_path}")

    # Get scaffold directory path
    scaffold_dir = Path(__file__).parent / "scaffold"

    # Copy scaffold contents to project
    for item in scaffold_dir.iterdir():
        # Skip __pycache__ directories
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
    click.echo("\nNext steps:")
    click.echo(f"  1. Add raw mast data (see {project_path}/pre-masts/README.md)")
    click.echo(f"  2. Download meso data (see {project_path}/mesos/README.md)")
    click.echo(f"  3. Run preprocessing in Claude Code: /preprocess-mast-data {project_path}/pre-masts")
    click.echo("  4. Generate config: julia bin/CleanMast.jl recommend parse-sensors")


# === Recommend command group ===


@main.group()
def recommend():
    """Generate configuration files for various processing steps."""
    pass


@recommend.command("extrapolate")
@click.argument("project_dir", type=click.Path(exists=True))
@click.option(
    "--extrapolate-heights",
    "-h",
    required=True,
    help="Comma-separated target heights in meters (e.g., 120,140,160)",
)
@click.option(
    "--strategy",
    "-s",
    default="top3-constant-shear",
    help=f"Strategy name. Available: {', '.join(list_strategies())}",
)
@click.option(
    "--representative-year-config",
    "-r",
    default=None,
    help="Path to representative-year.toml (default: representative-year.toml in project_dir)",
)
def recommend_extrapolate_wind(
    project_dir: str,
    extrapolate_heights: str,
    strategy: str,
    representative_year_config: str | None,
):
    """Generate vertical wind extrapolation configuration.

    Reads reconstruct-meso.toml to get mast output paths, then generates
    two config files with shear parameters fitted from top measurement layers:

    1. vertical-extrapolate-reconstruct-meso.toml - for reconstruct-meso output
    2. vertical-extrapolate-representative-year.toml - for representative-year output

    Both configs use shear values fitted from reconstruct-meso data.

    Example:

        uv run cleanmast recommend extrapolate projects/my-project -h 120,140,160
    """
    project_path = Path(project_dir)

    # Parse heights
    heights = [float(h.strip()) for h in extrapolate_heights.split(",")]
    click.echo(f"Target extrapolation heights: {heights}")

    # Load reconstruct-meso config
    reconstruct_meso_path = project_path / "reconstruct-meso.toml"
    if not reconstruct_meso_path.exists():
        raise click.ClickException(
            f"reconstruct-meso.toml not found at {reconstruct_meso_path}. "
            "Run this command after reconstruct-meso step."
        )

    with open(reconstruct_meso_path, "rb") as f:
        reconstruct_data = tomli.load(f)
    reconstruct_config = ReconstructMesoConfiguration(**reconstruct_data)
    click.echo(f"Loaded {len(reconstruct_config.masts)} mast(s) from reconstruct-meso.toml")

    # Load representative-year config (optional)
    rep_year_config: RepresentativeYearConfiguration | None = None
    if representative_year_config:
        rep_year_path = Path(representative_year_config)
    else:
        rep_year_path = project_path / "representative-year.toml"

    if rep_year_path.exists():
        rep_year_config = load_representative_year_config(str(rep_year_path))
        click.echo(
            f"Loaded {len(rep_year_config.masts)} mast(s) from {rep_year_path.name}"
        )
    else:
        click.echo(
            f"Warning: {rep_year_path.name} not found. "
            "Only generating reconstruct-meso extrapolation config."
        )

    # Get strategy and generate configs
    click.echo(f"Using strategy: {strategy}")
    strategy_class = get_strategy(strategy)
    strategy_instance = strategy_class()

    configs = strategy_instance.recommend(
        reconstruct_config=reconstruct_config,
        base_dir=str(project_path),
        extrapolate_heights=heights,
        representative_year_config=rep_year_config,
    )

    # Write config files
    for config_name, extrapolate_config in configs.items():
        output_path = project_path / config_name
        config_dict = extrapolate_config.model_dump()

        with open(output_path, "wb") as f:
            tomli_w.dump(config_dict, f)

        click.echo(f"\nGenerated: {output_path}")
        click.echo(f"  Strategy: {extrapolate_config.strategy}")
        click.echo(f"  Masts: {len(extrapolate_config.masts)}")

        # Show per-mast parameters
        for mast in extrapolate_config.masts:
            ws_heights = [h.height for h in mast.windspeed.heights]
            wd_heights = [h.height for h in mast.winddirection.heights]
            click.echo(f"\n  {mast.name}:")
            click.echo(f"    Wind speed heights: {ws_heights}")
            click.echo(f"    Wind direction heights: {wd_heights}")
            if mast.windspeed.heights:
                shear = mast.windspeed.heights[0].references[0].shear
                click.echo(f"    Fitted shear: {shear:.4f}")
            if mast.winddirection.heights:
                deg_diff = mast.winddirection.heights[0].references[0].deg_diff_per_m
                click.echo(f"    Fitted deg_diff_per_m: {deg_diff:.4f}")

    click.echo("\nNext steps:")
    for config_name in configs:
        click.echo(f"  uv run cleanmast extrapolate {project_path / config_name}")


# === Extrapolate command ===


@main.command()
@click.argument("config_path", type=click.Path(exists=True))
def extrapolate(config_path: str):
    """Execute vertical wind extrapolation.

    Reads vertical-extrapolate.toml and extrapolates wind speed and direction
    to target heights using power law shear model.

    Example:

        uv run cleanmast extrapolate projects/my-project/vertical-extrapolate.toml
    """
    config_path_obj = Path(config_path)
    base_dir = str(config_path_obj.parent)

    click.echo(f"Loading config: {config_path}")
    config = load_extrapolate_config(str(config_path_obj))

    click.echo(f"Strategy: {config.strategy}")
    click.echo(f"Masts: {len(config.masts)}")

    # Execute extrapolation
    click.echo("\nProcessing masts...")
    execute_extrapolation(str(config_path_obj))

    # Report results
    click.echo("\nExtrapolation complete!")
    for mast in config.masts:
        output_path = Path(base_dir) / mast.output.data
        ws_heights = [h.height for h in mast.windspeed.heights]
        wd_heights = [h.height for h in mast.winddirection.heights]
        click.echo(f"  {mast.name}: {output_path}")
        click.echo(f"    Extrapolated WS heights: {ws_heights}")
        click.echo(f"    Extrapolated WD heights: {wd_heights}")


if __name__ == "__main__":
    main()
