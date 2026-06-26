"""Assembly functions for representative year calibration atoms.

Pure functions only — NO IO, no side effects.
Takes computed results and wraps them in MultiMastRepYearCalibrationAtom instances.
"""

import polars as pl

from cleanmast.subdomains.reporting.subdomains.representative_year.model.report_meta import (
    RepresentativeYearAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.model.representative_year_atom import (
    MultiMastRepYearCalibrationAtom,
)
from cleanmast.subdomains.reporting.subdomains.representative_year.model.schemas import (
    MultiMastRepYearCalibrationSchema,
)


def build_representative_year_atoms(
    df: pl.DataFrame,
) -> list[MultiMastRepYearCalibrationAtom]:
    """Build MultiMastRepYearCalibrationAtom instances from computed data.

    Args:
        df: DataFrame matching MultiMastRepYearCalibrationSchema.

    Returns:
        Single-element list containing the atom for all masts.
    """
    mast_names = df["mast_name"].to_list()
    atom = MultiMastRepYearCalibrationAtom.create(
        MultiMastRepYearCalibrationSchema,
        df,
        RepresentativeYearAtomMeta(mast_names=mast_names),
    )
    return [atom]
