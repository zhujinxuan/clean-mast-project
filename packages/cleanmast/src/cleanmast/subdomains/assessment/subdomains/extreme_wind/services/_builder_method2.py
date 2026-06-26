"""Fifty-year max wind Method 2 section builder.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓ | Builder Pattern ✓
"""

from pathlib import Path

from cleanmast.subdomains.assessment.shared.protocols.report_atom import ReportAtom
from cleanmast.subdomains.assessment.subdomains.extreme_wind.entities.fifty_year_max_wind_method2_atom import (
    SingleMastFiftyYearMaxWindMethod2ParamsAtom,
    SingleMastFiftyYearMaxWindMethod2QQExtremeAtom,
    SingleMastFiftyYearMaxWindMethod2QQSustainedAtom,
    SingleMastFiftyYearMaxWindMethod2ResultAtom,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.value_objects.schemas import (
    FiftyYearMaxWindResultSchema,
    GumbelParameterSchema,
)


class Method2Builder:
    """Builds Method 2 subsection from analysis results into report atoms."""

    def build(
        self,
        mast_name: str,
        sustained_wind: AnalysisResult[FiftyYearMaxWindResultSchema],
        sustained_params: AnalysisResult[GumbelParameterSchema],
        extreme_wind: AnalysisResult[FiftyYearMaxWindResultSchema],
        extreme_params: AnalysisResult[GumbelParameterSchema],
        qq_output_dir: Path,
    ) -> list[ReportAtom]:
        """Build Method 2 subsection from analysis results to report atoms.

        Args:
            mast_name: Name of the mast being analyzed
            sustained_wind: Sustained wind analysis result
            sustained_params: Sustained Gumbel parameters
            extreme_wind: Extreme wind analysis result
            extreme_params: Extreme Gumbel parameters
            qq_output_dir: Directory for Q-Q plot output

        Returns:
            List of report atoms in order: Result, Params, QQSustained, QQExtreme
        """
        meta = SingleMastMeta(mast_name=mast_name)

        wind_df = sustained_wind.data
        if not extreme_wind.data.is_empty():
            wind_df = wind_df.vstack(extreme_wind.data)

        param_df = sustained_params.data
        if not extreme_params.data.is_empty():
            param_df = param_df.vstack(extreme_params.data)

        return [
            SingleMastFiftyYearMaxWindMethod2ResultAtom.create(
                schema=FiftyYearMaxWindResultSchema,
                df=wind_df,
                meta=meta,
            ),
            SingleMastFiftyYearMaxWindMethod2ParamsAtom.create(
                schema=GumbelParameterSchema,
                df=param_df,
                meta=meta,
            ),
            SingleMastFiftyYearMaxWindMethod2QQSustainedAtom.create(
                schema=GumbelParameterSchema,
                df=param_df,
                meta=meta,
            ),
            SingleMastFiftyYearMaxWindMethod2QQExtremeAtom.create(
                schema=GumbelParameterSchema,
                df=param_df,
                meta=meta,
            ),
        ]
