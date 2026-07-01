import polars as pl

from cleanmast.subdomains.reporting.model.analysis_result import AnalysisResult
from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.vertical_profile.model.report_meta import (
    VerticalProfileAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.vertical_profile.model.schemas import (
    VerticalProfileSchema,
    WindShearSchema,
)
from cleanmast.subdomains.reporting.subdomains.vertical_profile.model.wind_shear_exponent_atom import (
    create_single_mast_wind_shear_exponent_atom,
)


class VerticalProfileSectionBuilder:
    def build(
        self,
        mast_name: str,
        profile_results: list[AnalysisResult[VerticalProfileSchema]],
        shear_results: list[AnalysisResult[WindShearSchema]],
    ) -> list[ReportAtom]:
        profile_df = pl.concat([r.data for r in profile_results])
        shear_df = pl.concat([r.data for r in shear_results])

        meta = VerticalProfileAtomMeta(mast_name=mast_name)

        return [
            create_single_mast_wind_shear_exponent_atom(
                profile_schema=VerticalProfileSchema,
                profile_df=profile_df,
                shear_schema=WindShearSchema,
                shear_df=shear_df,
                meta=meta,
            )
        ]


def build_vertical_profile_atoms(
    mast_name: str,
    profile_results: list[AnalysisResult[VerticalProfileSchema]],
    shear_results: list[AnalysisResult[WindShearSchema]],
) -> list[ReportAtom]:
    return VerticalProfileSectionBuilder().build(
        mast_name, profile_results, shear_results
    )


__all__ = ["VerticalProfileSectionBuilder", "build_vertical_profile_atoms"]
