"""Weibull section builder.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓ | Builder Pattern ✓
"""

import polars as pl

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.entities.single_mast.weibull_distribution import (
    SingleMastWeibullDistributionAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.weibull_multi import (
    SingleMastWeibullMultiHeightAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.weibull_parameters import (
    SingleMastWeibullParametersAtom,
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
    converting analysis results into the 3 Weibull-related report atoms.
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
            List of 3 report atoms in order:
            1. SingleMastWeibullParametersAtom (all heights in one table)
            2. SingleMastWeibullDistributionAtom (per-height distribution charts)
            3. SingleMastWeibullMultiHeightAtom (multi-height comparison)
        """
        # Concatenate all results into single DataFrame
        df = pl.concat([r.data for r in results])
        meta = SingleMastMeta(mast_name=mast_name)

        atoms: list[ReportAtom] = [
            SingleMastWeibullParametersAtom.create(
                schema=WeibullSchema,
                df=df,
                meta=meta,
            ),
            SingleMastWeibullDistributionAtom.create(
                schema=WeibullSchema,
                df=df,
                meta=meta,
            ),
            SingleMastWeibullMultiHeightAtom.create(
                schema=WeibullSchema,
                df=df,
                meta=meta,
            ),
        ]

        return atoms
