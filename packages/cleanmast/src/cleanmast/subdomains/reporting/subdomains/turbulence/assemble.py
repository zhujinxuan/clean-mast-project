"""Assembly functions for turbulence intensity atoms.

Pure functions only — NO IO, no side effects.
Takes computed DataFrame and wraps them in report atom instances.
"""

import polars as pl

from cleanmast.subdomains.reporting.subdomains.turbulence.compute import (
    _select_interested_heights,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.model.report_meta import (
    TurbulenceAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.model.turbulence_multi_atom import (
    SingleMastTurbulenceMultiHeightAtom,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.model.turbulence_per_height_atom import (
    SingleMastTurbulencePerHeightAtom,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.model.turbulence_summary_atom import (
    SingleMastTurbulenceSummaryAtom,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.model.schemas import (
    TurbulenceSchema,
)
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom


def build_turbulence_atoms(
    ti_df: pl.DataFrame,
    mast_name: str,
) -> list[ReportAtom]:
    """Build turbulence section atoms from computed TI DataFrame.

    Returns atoms in order:
    1. SingleMastTurbulenceSummaryAtom (turbulence summary across heights)
    2..N. SingleMastTurbulencePerHeightAtom (one per interested height)
    N+1. SingleMastTurbulenceMultiHeightAtom (multi-height comparison)
    """
    meta = TurbulenceAtomMeta(mast_name=mast_name)
    unique_heights = ti_df["height"].unique().to_list()
    interested_heights = _select_interested_heights(unique_heights)

    atoms: list[ReportAtom] = [
        SingleMastTurbulenceSummaryAtom.create(
            schema=TurbulenceSchema,
            df=ti_df,
            meta=meta,
        ),
    ]

    for height in sorted(interested_heights):
        atoms.append(
            SingleMastTurbulencePerHeightAtom.create_with_height(
                schema=TurbulenceSchema,
                df=ti_df,
                meta=meta,
                height=height,
            )
        )

    atoms.append(
        SingleMastTurbulenceMultiHeightAtom.create(
            schema=TurbulenceSchema,
            df=ti_df,
            meta=meta,
        )
    )

    return atoms
