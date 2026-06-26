"""Fifty-year max wind summary section builder (private helper).

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓ | Builder Pattern ✓
"""

from cleanmast.subdomains.assessment.shared.protocols.report_atom import ReportAtom
from cleanmast.subdomains.assessment.subdomains.extreme_wind.entities.fifty_year_max_wind_summary_atom import (
    SingleMastFiftyYearMaxWindComparisonExtremeAtom,
    SingleMastFiftyYearMaxWindComparisonSustainedAtom,
    SingleMastIECWindClassAtom,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.services._calc_summary import (
    SummaryCalculator,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.value_objects.schemas import (
    FiftyYearMaxWindComparisonSchema,
    FiftyYearMaxWindMethod1DetailSchema,
    FiftyYearMaxWindResultSchema,
    IECWindClassSchema,
)


class SummaryBuilder:
    """Builds fifty-year max wind summary subsection from all method results."""

    def build(
        self,
        mast_name: str,
        method1_result: AnalysisResult[FiftyYearMaxWindMethod1DetailSchema],
        method2_sustained: AnalysisResult[FiftyYearMaxWindResultSchema],
        method2_extreme: AnalysisResult[FiftyYearMaxWindResultSchema],
        method3_sustained: AnalysisResult[FiftyYearMaxWindResultSchema],
        method3_extreme: AnalysisResult[FiftyYearMaxWindResultSchema],
    ) -> list[ReportAtom]:
        """Build summary subsection atoms from all method results.

        Args:
            mast_name: Name of the mast being analyzed
            method1_result: Method 1 detail result
            method2_sustained: Method 2 sustained result
            method2_extreme: Method 2 extreme result
            method3_sustained: Method 3 sustained result
            method3_extreme: Method 3 extreme result

        Returns:
            List of 3 report atoms: sustained comparison, extreme comparison, IEC wind class
        """
        sustained_comp, extreme_comp, iec = SummaryCalculator().calculate(
            method1_result=method1_result,
            method2_sustained=method2_sustained,
            method2_extreme=method2_extreme,
            method3_sustained=method3_sustained,
            method3_extreme=method3_extreme,
        )

        meta = SingleMastMeta(mast_name=mast_name)

        return [
            SingleMastFiftyYearMaxWindComparisonSustainedAtom.create(
                schema=FiftyYearMaxWindComparisonSchema,
                df=sustained_comp.data,
                meta=meta,
            ),
            SingleMastFiftyYearMaxWindComparisonExtremeAtom.create(
                schema=FiftyYearMaxWindComparisonSchema,
                df=extreme_comp.data,
                meta=meta,
            ),
            SingleMastIECWindClassAtom.create(
                schema=IECWindClassSchema,
                df=iec.data,
                meta=meta,
            ),
        ]
