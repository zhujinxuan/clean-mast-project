"""Turbulence section builder.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓ | Builder Pattern ✓
"""

import polars as pl

from cleanmast.subdomains.assessment.shared.protocols.report_atom import ReportAtom
from cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_multi_atom import (
    SingleMastTurbulenceMultiHeightAtom,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_per_height_atom import (
    SingleMastTurbulencePerHeightAtom,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_summary_atom import (
    SingleMastTurbulenceSummaryAtom,
)
from cleanmast.subdomains.assessment.shared.utils.height_filter import (
    select_interested_heights,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.value_objects.schemas import (
    TurbulenceSchema,
    TurbulenceSectorSchema,
)


class TurbulenceSectionBuilder:
    """Builds turbulence section from analysis results into report atoms.

    Bridges the analysis layer (TurbulenceCalculator) with the reporting layer,
    converting analysis results into the 4 turbulence-related report atoms.
    """

    def build(
        self,
        mast_name: str,
        ti_results: list[AnalysisResult[TurbulenceSchema]],
        sector_results: list[AnalysisResult[TurbulenceSectorSchema]] | None = None,
    ) -> list[ReportAtom]:
        """Build turbulence section from analysis results to report atoms.

        Args:
            mast_name: Name of the mast being analyzed
            ti_results: List of turbulence intensity results, one per height
            sector_results: Deprecated, kept for API compatibility.

        Returns:
            List of report atoms in order:
            1. SingleMastTurbulenceSummaryAtom (turbulence summary across heights)
            2..N. SingleMastTurbulencePerHeightAtom (one per interested height)
            N+1. SingleMastTurbulenceMultiHeightAtom (multi-height comparison)
        """
        # Concatenate TI results into single DataFrame
        ti_df = pl.concat([r.data for r in ti_results])
        meta = SingleMastMeta(mast_name=mast_name)
        unique_heights = ti_df["height"].unique().to_list()
        interested_heights = select_interested_heights(unique_heights)

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
