"""Vertical profile section builder.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓ | Builder Pattern ✓
"""

import polars as pl

from cleanmast.subdomains.assessment.shared.protocols.report_atom import ReportAtom
from cleanmast.subdomains.assessment.subdomains.vertical_profile.entities.wind_shear_matrix_atom import (
    SingleMastWindShearExponentAtom,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.subdomains.vertical_profile.value_objects.schemas import (
    VerticalProfileSchema,
    WindShearSchema,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)


class VerticalProfileSectionBuilder:
    """Builds vertical profile and wind shear section from analysis results into a single report atom.

    Bridges the analysis layer (VerticalProfileCalculator, WindShearCalculator)
    with the reporting layer, converting analysis results into a single report atom:
    the wind shear exponent matrix.
    """

    def build(
        self,
        mast_name: str,
        profile_results: list[AnalysisResult[VerticalProfileSchema]],
        shear_results: list[AnalysisResult[WindShearSchema]],
    ) -> list[ReportAtom]:
        """Build vertical profile section from analysis results to a report atom.

        Args:
            mast_name: Name of the mast being analyzed
            profile_results: List of vertical profile results, one per height
            shear_results: List of wind shear results, one per height pair

        Returns:
            List containing 1 report atom:
            SingleMastWindShearExponentAtom (wind shear exponent matrix)
        """
        # Concatenate profile results into single DataFrame
        profile_df = pl.concat([r.data for r in profile_results])

        # Concatenate shear results into single DataFrame
        shear_df = pl.concat([r.data for r in shear_results])

        meta = SingleMastMeta(mast_name=mast_name)

        return [
            SingleMastWindShearExponentAtom.create(
                profile_schema=VerticalProfileSchema,
                profile_df=profile_df,
                shear_schema=WindShearSchema,
                shear_df=shear_df,
                meta=meta,
            )
        ]
