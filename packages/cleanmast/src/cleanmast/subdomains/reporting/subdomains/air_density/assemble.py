"""Assembly functions for air density atoms.

Pure functions only — NO IO, no side effects.
Takes computed results and wraps them in MultiMastAirDensityAtom instances.
"""

import polars as pl

from cleanmast.subdomains.reporting.subdomains.air_density.model.air_density_atom import (
    MultiMastAirDensityAtom,
)
from cleanmast.subdomains.reporting.subdomains.air_density.model.report_meta import (
    AirDensityAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.air_density.model.schemas import (
    AirDensitySchema,
)


def build_air_density_atoms(
    rows: list[dict[str, str | float | None]],
) -> list[MultiMastAirDensityAtom]:
    """Build MultiMastAirDensityAtom instances from computed row data.

    Args:
        rows: List of dicts with keys: mast_name, temperature, pressure,
              ground_air_density, reference_height.

    Returns:
        Single-element list containing the MultiMastAirDensityAtom
        for all masts.
    """
    df = pl.DataFrame(rows)
    mast_names = [str(r["mast_name"]) for r in rows]
    atom = MultiMastAirDensityAtom.create(
        AirDensitySchema,
        df,
        AirDensityAtomMeta(mast_names=mast_names),
    )
    return [atom]
