"""Fifty-year max wind Method 1 section builder.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓ | Builder Pattern ✓
"""

from cleanmast.subdomains.assessment.shared.protocols.report_atom import ReportAtom
from cleanmast.subdomains.assessment.subdomains.extreme_wind.entities.fifty_year_max_wind_method1_atom import (
    SingleMastFiftyYearMaxWindMethod1Atom,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.value_objects.schemas import (
    FiftyYearMaxWindMethod1DetailSchema,
)


class Method1Builder:
    """Builds Method 1 subsection from analysis result into report atoms."""

    def build(
        self,
        mast_name: str,
        result: AnalysisResult[FiftyYearMaxWindMethod1DetailSchema],
    ) -> list[ReportAtom]:
        """Build Method 1 subsection from analysis result to report atoms.

        Args:
            mast_name: Name of the mast being analyzed
            result: Method 1 analysis result

        Returns:
            List containing one SingleMastFiftyYearMaxWindMethod1Atom
        """
        meta = SingleMastMeta(mast_name=mast_name)
        return [
            SingleMastFiftyYearMaxWindMethod1Atom.create(
                schema=FiftyYearMaxWindMethod1DetailSchema,
                df=result.data,
                meta=meta,
            ),
        ]
