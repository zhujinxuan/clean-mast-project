"""Assembly functions for extreme wind atoms.

Pure functions only — NO IO, no side effects.
"""

import polars as pl

from cleanmast.subdomains.reporting.subdomains.extreme_wind.compute import (
    MastComparison,
    build_iec_class_table,
    build_site_conclusion_sentences,
    build_site_determination_table,
    build_summary_comparison,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.iec_atom import (
    IEC_STANDARDS_DATA,
    IECStandardsAtom,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.method1_atom import (
    Method1Atom,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.method2_atom import (
    Method2ParamsAtom,
    Method2QQExtremeAtom,
    Method2QQSustainedAtom,
    Method2ResultAtom,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.method3_atom import (
    Method3Atom,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.report_meta import (
    ExtremeWindAtomMeta,
    IECStandardsAtomMeta,
    SiteLevelAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.schemas import (
    FiftyYearMaxWindComparisonSchema,
    FiftyYearMaxWindMethod1DetailSchema,
    FiftyYearMaxWindResultSchema,
    GumbelParameterSchema,
    IECStandardsSchema,
    IECWindClassSchema,
    SiteConclusionSchema,
    SiteDeterminationSchema,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.site_atom import (
    SiteConclusionAtom,
    SiteDeterminationAtom,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.summary_atom import (
    ComparisonExtremeAtom,
    ComparisonSustainedAtom,
    IECWindClassAtom,
)


def build_method1_atom(
    mast_name: str,
    df: pl.DataFrame,
) -> Method1Atom:
    """Build Method1Atom from computed DataFrame.

    Args:
        mast_name: Name of the mast.
        df: DataFrame with FiftyYearMaxWindMethod1DetailSchema columns.

    Returns:
        Method1Atom instance.
    """
    return Method1Atom.create(
        schema=FiftyYearMaxWindMethod1DetailSchema,
        df=df,
        meta=ExtremeWindAtomMeta(mast_name=mast_name),
    )


def build_method2_atoms(
    mast_name: str,
    wind_df: pl.DataFrame,
    param_df: pl.DataFrame,
) -> list[Method2ResultAtom | Method2ParamsAtom | Method2QQSustainedAtom | Method2QQExtremeAtom]:
    """Build Method2 atoms (result, params, QQ sustained, QQ extreme).

    Args:
        mast_name: Name of the mast.
        wind_df: Combined sustained + extreme wind result DataFrame.
        param_df: Combined sustained + extreme parameters DataFrame.

    Returns:
        List of 4 atoms in order: Result, Params, QQSustained, QQExtreme.
    """
    meta = ExtremeWindAtomMeta(mast_name=mast_name)
    return [
        Method2ResultAtom.create(
            schema=FiftyYearMaxWindResultSchema,
            df=wind_df,
            meta=meta,
        ),
        Method2ParamsAtom.create(
            schema=GumbelParameterSchema,
            df=param_df,
            meta=meta,
        ),
        Method2QQSustainedAtom.create(
            schema=GumbelParameterSchema,
            df=param_df,
            meta=meta,
        ),
        Method2QQExtremeAtom.create(
            schema=GumbelParameterSchema,
            df=param_df,
            meta=meta,
        ),
    ]


def build_method3_atom(
    mast_name: str,
    sustained_df: pl.DataFrame,
    extreme_df: pl.DataFrame,
) -> Method3Atom:
    """Build Method3Atom from sustained and extreme DataFrames.

    Both sustained and extreme rows are passed through (mirroring
    Method 1/Method 2 rendering).

    Args:
        mast_name: Name of the mast.
        sustained_df: Sustained wind result DataFrame.
        extreme_df: Extreme wind result DataFrame.

    Returns:
        Method3Atom instance.
    """
    return Method3Atom.create(
        schema=FiftyYearMaxWindResultSchema,
        df=pl.concat([sustained_df, extreme_df]),
        meta=ExtremeWindAtomMeta(mast_name=mast_name),
    )


def build_site_conclusion_atoms(
    mast_comparisons: list[MastComparison],
) -> list[SiteDeterminationAtom | SiteConclusionAtom]:
    """Build site-level cross-mast determination + conclusion atoms.

    Args:
        mast_comparisons: Per-mast (mast_name, sustained comparison,
            extreme comparison) bundles from build_summary_comparison.

    Returns:
        List of 2 atoms (determination table, conclusion paragraph),
        or an empty list when no mast produced comparison rows.
    """
    determination = build_site_determination_table(mast_comparisons)
    sentences = build_site_conclusion_sentences(mast_comparisons)
    if determination.is_empty() or not sentences:
        return []

    meta = SiteLevelAtomMeta()
    return [
        SiteDeterminationAtom.create(
            schema=SiteDeterminationSchema,
            df=determination,
            meta=meta,
        ),
        SiteConclusionAtom.create(
            schema=SiteConclusionSchema,
            df=pl.DataFrame({"text": sentences}),
            meta=meta,
        ),
    ]


def build_summary_atoms(
    mast_name: str,
    method1_df: pl.DataFrame,
    method2_df: pl.DataFrame,
    method3_df: pl.DataFrame,
) -> list[ComparisonSustainedAtom | ComparisonExtremeAtom | IECWindClassAtom]:
    """Build summary comparison and IEC classification atoms.

    Args:
        mast_name: Name of the mast.
        method1_df: Method 1 detail DataFrame.
        method2_df: Method 2 result DataFrame.
        method3_df: Method 3 result DataFrame.

    Returns:
        List of 3 atoms: sustained comparison, extreme comparison, IEC wind class.
    """
    sustained_comp = build_summary_comparison(
        method1_df, method2_df, method3_df, "sustained"
    )
    extreme_comp = build_summary_comparison(
        method1_df, method2_df, method3_df, "extreme"
    )
    iec_table = build_iec_class_table(sustained_comp, extreme_comp)

    meta = ExtremeWindAtomMeta(mast_name=mast_name)

    return [
        ComparisonSustainedAtom.create(
            schema=FiftyYearMaxWindComparisonSchema,
            df=sustained_comp,
            meta=meta,
        ),
        ComparisonExtremeAtom.create(
            schema=FiftyYearMaxWindComparisonSchema,
            df=extreme_comp,
            meta=meta,
        ),
        IECWindClassAtom.create(
            schema=IECWindClassSchema,
            df=iec_table,
            meta=meta,
        ),
    ]


def build_iec_standards_atom() -> IECStandardsAtom:
    """Build the IEC 61400-1 standards reference atom (not mast-specific).

    Returns:
        IECStandardsAtom instance.
    """
    return IECStandardsAtom.create(
        schema=IECStandardsSchema,
        df=IEC_STANDARDS_DATA,
        meta=IECStandardsAtomMeta(),
    )
