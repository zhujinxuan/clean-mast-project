"""CLI adapters for the process command group.

ADR-GUARDRAILS: cli-001-comonicon-cli, structure-001-subdomain-layout
"""

import click


@click.command()
@click.option("--config", required=True, type=click.Path(exists=True))
def reconstruct_single(config: str):
    """Reconstruct data using single-mast correlation."""
    raise NotImplementedError(
        "Single-mast reconstruction is not yet implemented in Python. "
        "Use: julia bin/CleanMast.jl reconstruct-single"
    )


@click.command()
@click.option("--config", required=True, type=click.Path(exists=True))
def reconstruct_meso(config: str):
    """Reconstruct data using mesoscale correlation."""
    raise NotImplementedError(
        "Mesoscale reconstruction is not yet implemented in Python. "
        "Use: julia bin/CleanMast.jl reconstruct-meso"
    )
