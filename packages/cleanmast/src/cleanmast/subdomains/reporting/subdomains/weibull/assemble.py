"""Assembly functions for Weibull atoms.

Pure functions only — NO IO, no side effects.
Takes computed fit results and wraps them in WeibullSubgridAtom instances.
"""

import polars as pl

from cleanmast.subdomains.reporting.subdomains.weibull.compute import (
    WeibullFitResult,
)
from cleanmast.subdomains.reporting.subdomains.weibull.model.report_meta import (
    WeibullAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.weibull.model.schemas import (
    WeibullSchema,
)
from cleanmast.subdomains.reporting.subdomains.weibull.model.weibull_atom import (
    WeibullSubgridAtom,
)


def build_weibull_atoms(
    mast_name: str,
    fit_results: list[WeibullFitResult],
) -> list[WeibullSubgridAtom]:
    """Build WeibullSubgridAtom instances from fit results.

    Args:
        mast_name: Name of the mast.
        fit_results: List of WeibullFitResult, one per height.

    Returns:
        Single-element list containing the WeibullSubgridAtom.
    """
    rows = [
        {
            "height": r.height,
            "interpolation_marker": r.interpolation_marker,
            "shape_k": r.shape_k,
            "scale_c": r.scale_c,
            "mean_speed": r.mean_speed,
            "bin_centers": r.bin_centers,
            "observed_density": r.observed_density,
            "fitted_density": r.fitted_density,
        }
        for r in fit_results
    ]

    df = pl.DataFrame(rows)
    meta = WeibullAtomMeta(mast_name=mast_name)
    atom = WeibullSubgridAtom.create(
        schema=WeibullSchema,
        df=df,
        meta=meta,
    )
    return [atom]
