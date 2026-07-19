"""Extreme wind gust factor — reporting domain runtime carrier."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtremeWindGustFactor:
    """Per-height gust factor for converting 10min avg to 3s extreme.

    Attributes:
        height: Measurement height in meters.
        gust_factor: Gust factor (10min→3s conversion), defaults to 1.4.
    """

    height: float
    gust_factor: float = 1.4
