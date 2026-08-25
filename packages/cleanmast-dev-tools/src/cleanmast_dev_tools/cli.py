"""CLI entry point for CleanMast developer tools."""

import click

from .verify import verify


@click.command(
    "baseline",
    context_settings={"ignore_unknown_options": True},
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def baseline(args: tuple[str, ...]) -> None:
    """Run the six-check verification baseline (ty, ruff, pytest, dvc-verify, ast-grep, lint-imports).

    All arguments are passed through to the argparse runner, e.g.:
    cleanmast-dev baseline --package cleanmast --skip dvc --skip pytest
    """
    from .baseline import main as baseline_main

    raise SystemExit(baseline_main(list(args)))


@click.group()
def main():
    """CleanMast developer tools — repo-fixture-driven commands, never shipped to end users."""


# Register commands
main.add_command(verify, "verify")
main.add_command(baseline)
