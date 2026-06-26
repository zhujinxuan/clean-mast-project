"""Fifty-year max wind Method 3 section builder.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓ | Builder Pattern ✓
"""

import polars as pl

from cleanmast.subdomains.assessment.shared.protocols.report_atom import ReportAtom
from cleanmast.subdomains.assessment.subdomains.extreme_wind.entities.fifty_year_max_wind_method3_atom import (
    SingleMastFiftyYearMaxWindMethod3Atom,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.value_objects.schemas import (
    FiftyYearMaxWindResultSchema,
)


class Method3Builder:
    """Builds Method 3 subsection from sustained and extreme analysis results into report atoms."""

    def build(
        self,
        mast_name: str,
        sustained_result: AnalysisResult[FiftyYearMaxWindResultSchema],
        extreme_result: AnalysisResult[FiftyYearMaxWindResultSchema],
    ) -> list[ReportAtom]:
        """Build Method 3 subsection from analysis results to report atoms.

        Args:
            mast_name: Name of the mast being analyzed
            sustained_result: Method 3 sustained analysis result
            extreme_result: Method 3 extreme analysis result

        Returns:
            List containing one SingleMastFiftyYearMaxWindMethod3Atom
        """
        meta = SingleMastMeta(mast_name=mast_name)
        combined_df = pl.concat([sustained_result.data, extreme_result.data])
        return [
            SingleMastFiftyYearMaxWindMethod3Atom.create(
                schema=FiftyYearMaxWindResultSchema,
                df=combined_df,
                meta=meta,
            ),
        ]
