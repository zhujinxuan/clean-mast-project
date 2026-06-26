"""Typed input dataclasses for reporting section construction.

Each section class receives a list of one of these input types in its
from_inputs classmethod. This replaces ad-hoc tuple formats.
"""

from dataclasses import dataclass
from datetime import datetime

from cleanmast.shared.timeseries import TimeSeriesData


@dataclass(frozen=True)
class MesoSectionInput:
    """Input for representative year calibration.
    
    Carries mesoscale (ERA5) data, NOT the mast's own timeseries.
    The calculation compares meso data's long-term average vs.
    the mast's representative-year subset.
    
    Used by: representative_year.
    """
    meso_time_series: TimeSeriesData
    mast_name: str
    meso_name: str
    rep_year_min: datetime
    rep_year_max: datetime
