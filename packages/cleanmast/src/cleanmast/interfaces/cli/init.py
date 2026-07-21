"""CLI adapter for project initialization command.

ADR-GUARDRAILS: cli-001-comonicon-cli, structure-001-subdomain-layout
"""

import shutil
from pathlib import Path

import click


@click.command()
@click.argument("project_dir", type=click.Path())
def init(project_dir: str):
    """Initialize a new project with template structure."""
    project_path = Path(project_dir)

    if not project_path.exists():
        project_path.mkdir(parents=True)
        click.echo(f"Created project directory: {project_path}")
    else:
        click.echo(f"Project directory exists: {project_path}")

    scaffold_dir = Path(__file__).parents[2] / "scaffold"

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
