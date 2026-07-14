"""Assembly functions for turbulence intensity atoms.

Pure functions only — NO IO, no side effects.
Takes computed DataFrame and wraps them in report atom instances.
"""

from typing import Sequence

import polars as pl

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.turbulence.model.report_meta import (
    TurbulenceAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.turbulence.model.schemas import (
    TurbulenceSchema,
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


def build_turbulence_atoms(
    mast_data: Sequence[tuple[str, pl.DataFrame]],
    mast_turbulence_heights: dict[str, list[float]],
) -> list[ReportAtom]:
    """Build turbulence section atoms from computed per-mast DataFrames.

    Args:
        mast_data: Sequence of (mast_name, ti_df) tuples.
        mast_turbulence_heights: Per-mast selected heights.

    Returns atoms in order per mast:
    1. SingleMastTurbulenceSummaryAtom (turbulence summary across heights)
    2..N. SingleMastTurbulencePerHeightAtom (one per interested height)
    N+1. SingleMastTurbulenceMultiHeightAtom (multi-height comparison)
    """
    atoms: list[ReportAtom] = []
    for mast_name, ti_df in mast_data:
        interested_heights = mast_turbulence_heights[mast_name]

        meta = TurbulenceAtomMeta(
            mast_name=mast_name,
            interested_heights=interested_heights,
        )

        atoms.append(
            SingleMastTurbulenceSummaryAtom.create(
                schema=TurbulenceSchema,
                df=ti_df,
                meta=meta,
            )
        )

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
