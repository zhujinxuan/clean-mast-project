"""Weibull section builder.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓ | Builder Pattern ✓
"""

import polars as pl

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.entities.single_mast.weibull_subgrid import (
    SingleMastWeibullSubgridAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WeibullSchema,
)


class WeibullSectionBuilder:
    """Builds Weibull section from analysis results into report atoms.

    Bridges the analysis layer (WeibullAnalyzer) with the reporting layer,
    converting analysis results into the Weibull-related report atom.
    """

    def build(
        self,
        mast_name: str,
        results: list[AnalysisResult[WeibullSchema]],
    ) -> list[ReportAtom]:
        """Build Weibull section from analysis results to report atoms.

        Args:
            mast_name: Name of the mast being analyzed
            results: List of analysis results, one per height

        Returns:
            List containing 1 report atom:
            1. SingleMastWeibullSubgridAtom (combined parameters and distribution)
        """
        # Concatenate all results into single DataFrame
        df = pl.concat([r.data for r in results])
        meta = SingleMastMeta(mast_name=mast_name)

        atoms: list[ReportAtom] = [
            SingleMastWeibullSubgridAtom.create(
                schema=WeibullSchema,
                df=df,
                meta=meta,
            ),
        ]

        return atoms
