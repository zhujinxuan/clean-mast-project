"""Assembly functions for wind rose atoms.

Pure functions only — NO IO, no side effects.
Takes computed DataFrame and wraps it in atom instances.
"""

import polars as pl

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.report_meta import (
    WindRoseAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.schemas import (
    WindRoseSchema,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.wind_rose_atom import (
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.wind_rose_grid_atom import (
    SingleMastMonthlyWindRoseGridAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_rose.model.wind_rose_power_grid_atom import (
    SingleMastMonthlyWindPowerRoseGridAtom,
)


def build_wind_rose_atoms(
    mast_name: str,
    df: pl.DataFrame,
) -> list[ReportAtom]:
    """Build wind rose report atoms from computed wind rose data.

    Args:
        mast_name: Name of the mast
        df: Computed wind rose DataFrame (WindRoseSchema format)

    Returns:
        List of 4 report atoms in order:
        1. SingleMastMonthlyWindFrequencyRoseAtom
        2. SingleMastWindPowerRoseAtom
        3. SingleMastMonthlyWindRoseGridAtom
        4. SingleMastMonthlyWindPowerRoseGridAtom
    """
    meta = WindRoseAtomMeta(mast_name=mast_name)

    atoms: list[ReportAtom] = [
        SingleMastMonthlyWindFrequencyRoseAtom.create(
            schema=WindRoseSchema,
            df=df,
            meta=meta,
        ),
        SingleMastWindPowerRoseAtom.create(
            schema=WindRoseSchema,
            df=df,
            meta=meta,
        ),
        SingleMastMonthlyWindRoseGridAtom.create(
            schema=WindRoseSchema,
            df=df,
            meta=meta,
        ),
        SingleMastMonthlyWindPowerRoseGridAtom.create(
            schema=WindRoseSchema,
            df=df,
            meta=meta,
        ),
    ]

    return atoms
