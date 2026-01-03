"""CleanMast CLI entry point."""

import shutil
from pathlib import Path

import click


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


if __name__ == "__main__":
    main()
