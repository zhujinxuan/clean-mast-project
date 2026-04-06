"""Vertical profile section builder.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service ✓ | Builder Pattern ✓
"""

import polars as pl

from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
from cleanmast.subdomains.assessment.domain.entities.single_mast.vertical_profile import (
    SingleMastVerticalProfileAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_shear_matrix import (
    SingleMastWindShearExponentAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_shear_table import (
    SingleMastWindShearTableAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.domain.value_objects.schemas import (
    VerticalProfileSchema,
    WindShearSchema,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)


class VerticalProfileSectionBuilder:
    """Builds vertical profile and wind shear section from analysis results into report atoms.

    Bridges the analysis layer (VerticalProfileCalculator, WindShearCalculator)
    with the reporting layer, converting analysis results into the 3 report atoms:
    vertical profile, wind shear table, and wind shear exponent matrix.
    """

    def build(
        self,
        mast_name: str,
        profile_results: list[AnalysisResult[VerticalProfileSchema]],
        shear_results: list[AnalysisResult[WindShearSchema]],
    ) -> list[ReportAtom]:
        """Build vertical profile section from analysis results to report atoms.

        Args:
            mast_name: Name of the mast being analyzed
            profile_results: List of vertical profile results, one per height
            shear_results: List of wind shear results, one per height pair

        Returns:
            List of 3 report atoms in order:
            1. SingleMastVerticalProfileAtom (vertical wind profile with power law fit)
            2. SingleMastWindShearTableAtom (wind shear statistics table)
            3. SingleMastWindShearExponentAtom (wind shear exponent matrix)
        """
        # Concatenate profile results into single DataFrame
        profile_df = pl.concat([r.data for r in profile_results])

        # Concatenate shear results into single DataFrame
        shear_df = pl.concat([r.data for r in shear_results])

        meta = SingleMastMeta(mast_name=mast_name)

        atoms: list[ReportAtom] = [
            SingleMastVerticalProfileAtom.create(
                schema=VerticalProfileSchema,
                df=profile_df,
                meta=meta,
            ),
            SingleMastWindShearTableAtom.create(
                schema=WindShearSchema,
                df=shear_df,
                meta=meta,
            ),
            SingleMastWindShearExponentAtom.create(
                schema=WindShearSchema,
                df=shear_df,
                meta=meta,
            ),
        ]

        return atoms
