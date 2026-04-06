"""Turbulence section builder.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓ | Builder Pattern ✓
"""

import polars as pl

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_intensity import (
    SingleMastTurbulenceIntensityAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_multi import (
    SingleMastTurbulenceMultiHeightAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_sector import (
    SingleMastTurbulenceSectorAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_summary import (
    SingleMastTurbulenceSummaryAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
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
        sector_results: list[AnalysisResult[TurbulenceSectorSchema]],
    ) -> list[ReportAtom]:
        """Build turbulence section from analysis results to report atoms.

        Args:
            mast_name: Name of the mast being analyzed
            ti_results: List of turbulence intensity results, one per height
            sector_results: List of turbulence sector results, one per height

        Returns:
            List of 4 report atoms in order:
            1. SingleMastTurbulenceSummaryAtom (turbulence summary across heights)
            2. SingleMastTurbulenceIntensityAtom (TI by wind speed bin)
            3. SingleMastTurbulenceMultiHeightAtom (multi-height comparison)
            4. SingleMastTurbulenceSectorAtom (TI by direction sector)
        """
        # Concatenate TI results into single DataFrame
        ti_df = pl.concat([r.data for r in ti_results])
        # Concatenate sector results into single DataFrame
        sector_df = pl.concat([r.data for r in sector_results])
        meta = SingleMastMeta(mast_name=mast_name)

        atoms: list[ReportAtom] = [
            SingleMastTurbulenceSummaryAtom.create(
                schema=TurbulenceSchema,
                df=ti_df,
                meta=meta,
            ),
            SingleMastTurbulenceIntensityAtom.create(
                schema=TurbulenceSchema,
                df=ti_df,
                meta=meta,
            ),
            SingleMastTurbulenceMultiHeightAtom.create(
                schema=TurbulenceSchema,
                df=ti_df,
                meta=meta,
            ),
            SingleMastTurbulenceSectorAtom.create(
                schema=TurbulenceSectorSchema,
                df=sector_df,
                meta=meta,
            ),
        ]

        return atoms
