"""Assembly functions for wind temporal atoms.

Pure functions only — NO IO, no side effects.
Takes computed DataFrames and wraps them in the 6 temporal pattern atoms.
"""

import polars as pl

from cleanmast.subdomains.reporting.protocols.report_atom import ReportAtom
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.daily_pattern_atom import (
    SingleMastDailyPatternAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.daily_power_pattern_atom import (
    SingleMastDailyPowerPatternAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.monthly_daily_power_atom import (
    SingleMastMonthlyDailyPowerAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.monthly_daily_wind_atom import (
    SingleMastMonthlyDailyWindAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.monthly_pattern_atom import (
    SingleMastMonthlyPatternAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.monthly_power_pattern_atom import (
    SingleMastMonthlyPowerPatternAtom,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.report_meta import (
    WindTemporalAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.wind_temporal.model.schemas import (
    TemporalPatternSchema,
)


def build_wind_temporal_atoms(
    mast_name: str,
    daily_df: pl.DataFrame,
    monthly_df: pl.DataFrame,
    monthly_daily_df: pl.DataFrame,
) -> list[ReportAtom]:
    """Build the 6 temporal pattern atoms from computed DataFrames.

    Args:
        mast_name: Name of the mast being analyzed.
        daily_df: DataFrame matching TemporalPatternSchema for daily pattern.
        monthly_df: DataFrame matching TemporalPatternSchema for monthly pattern.
        monthly_daily_df: DataFrame matching TemporalPatternSchema for monthly-daily pattern.

    Returns:
        List of 6 report atoms in order:
        1. SingleMastMonthlyPatternAtom
        2. SingleMastMonthlyPowerPatternAtom
        3. SingleMastDailyPatternAtom
        4. SingleMastDailyPowerPatternAtom
        5. SingleMastMonthlyDailyWindAtom
        6. SingleMastMonthlyDailyPowerAtom
    """
    meta = WindTemporalAtomMeta(mast_name=mast_name)

    return [
        SingleMastMonthlyPatternAtom.create(
            schema=TemporalPatternSchema,
            df=monthly_df,
            meta=meta,
        ),
        SingleMastMonthlyPowerPatternAtom.create(
            schema=TemporalPatternSchema,
            df=monthly_df,
            meta=meta,
        ),
        SingleMastDailyPatternAtom.create(
            schema=TemporalPatternSchema,
            df=daily_df,
            meta=meta,
        ),
        SingleMastDailyPowerPatternAtom.create(
            schema=TemporalPatternSchema,
            df=daily_df,
            meta=meta,
        ),
        SingleMastMonthlyDailyWindAtom.create(
            schema=TemporalPatternSchema,
            df=monthly_daily_df,
            meta=meta,
        ),
        SingleMastMonthlyDailyPowerAtom.create(
            schema=TemporalPatternSchema,
            df=monthly_daily_df,
            meta=meta,
        ),
    ]


__all__ = ["build_wind_temporal_atoms"]
