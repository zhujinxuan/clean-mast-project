"""Regression tests for wind rose month×sector zero-fill.

`_process_sensor_data` groups by (month, sector); a zero-count combination
emits no row. Downstream atoms average `frequency` / `energy_frequency` over
months per sector, so a seasonally-absent sector was divided by
"months present" instead of "months with data", inflating its share (sector
frequencies summed past 100%). The fix zero-fills every (observed month ×
sector) cell; months absent from the sensor's data are NOT fabricated.
"""

import polars as pl
import pytest
from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
from cleanmast.subdomains.reporting.subdomains.wind_rose.compute import (
    SECTOR_COUNT,
    calculate_wind_rose,
)

NORTH_SECTOR = 0
SOUTH_SECTOR = 8


def _monthly_time_series(
    months: list[int], wind_directions: list[float]
) -> TimeSeriesData:
    """One row per day (28 days) per month at 100 m, constant ws = 8 m/s.

    ``wind_directions`` holds one direction shared by every day of the
    corresponding month in ``months``.
    """
    timestamps: list[str] = []
    wd_values: list[float] = []
    for month, direction in zip(months, wind_directions, strict=True):
        for day in range(1, 29):
            timestamps.append(f"2024-{month:02d}-{day:02d}T00:00:00")
            wd_values.append(direction)

    df = pl.DataFrame({
        "timestamp": pl.Series(timestamps).str.to_datetime(),
        "WS_100m_avg": [8.0] * len(timestamps),
        "WD_100m_avg": wd_values,
    })

    sensors = [
        SensorColumn(
            column_name="WS_100m_avg",
            sensor_type="WindSpeed",
            sensor_direction="",
            height=100.0,
            stat_type="avg",
            unit="m/s",
        ),
        SensorColumn(
            column_name="WD_100m_avg",
            sensor_type="WindDirection",
            sensor_direction="",
            height=100.0,
            stat_type="avg",
            unit="deg",
        ),
    ]
    return TimeSeriesData(df=df, sensors=sensors)


def _sector_monthly_means(result: pl.DataFrame, column: str) -> dict[int, float]:
    """Mirror the atoms' aggregation: mean over months per sector."""
    means = result.group_by("sector").agg(pl.col(column).mean().alias("value"))
    return dict(zip(means["sector"].to_list(), means["value"].to_list(), strict=True))


class TestWindRoseZeroFill:
    def test_seasonally_absent_sector_zero_filled(self) -> None:
        """11 months all-N + 1 month all-S: N = 11/12, S = 1/12, sum = 1.0.

        Without zero-fill both sectors averaged 1.0 (present-only denominator)
        and the per-height sector sum reached 2.0.
        """
        time_series = _monthly_time_series(
            months=list(range(1, 13)), wind_directions=[0.0] * 11 + [180.0]
        )

        result = calculate_wind_rose(time_series, air_density=1.225, heights=[100.0])

        # Full grid: 12 observed months × 16 sectors
        assert len(result) == 12 * SECTOR_COUNT

        # Filled cells are explicit zeros in the frame itself
        december_north = result.filter(
            (pl.col("month") == 12) & (pl.col("sector") == NORTH_SECTOR)
        )
        assert len(december_north) == 1
        assert december_north["frequency"][0] == 0.0
        assert december_north["energy_frequency"][0] == 0.0

        freq_means = _sector_monthly_means(result, "frequency")
        assert pytest.approx(freq_means[NORTH_SECTOR], abs=1e-9) == 11 / 12
        assert pytest.approx(freq_means[SOUTH_SECTOR], abs=1e-9) == 1 / 12
        absent = [v for s, v in freq_means.items() if s not in (NORTH_SECTOR, SOUTH_SECTOR)]
        assert absent and all(v == 0.0 for v in absent)
        assert pytest.approx(sum(freq_means.values()), abs=1e-9) == 1.0

        energy_means = _sector_monthly_means(result, "energy_frequency")
        assert pytest.approx(energy_means[NORTH_SECTOR], abs=1e-9) == 11 / 12
        assert pytest.approx(energy_means[SOUTH_SECTOR], abs=1e-9) == 1 / 12
        assert pytest.approx(sum(energy_means.values()), abs=1e-9) == 1.0

    def test_absent_month_not_fabricated(self) -> None:
        """A month with no data is missing data, not zero frequency.

        Months 1..11 only, all-N: December must not appear as rows, and N
        (present every observed month) keeps a monthly mean of 1.0.
        """
        time_series = _monthly_time_series(
            months=list(range(1, 12)), wind_directions=[0.0] * 11
        )

        result = calculate_wind_rose(time_series, air_density=1.225, heights=[100.0])

        assert set(result["month"].unique().to_list()) == set(range(1, 12))
        assert len(result) == 11 * SECTOR_COUNT

        freq_means = _sector_monthly_means(result, "frequency")
        assert pytest.approx(sum(freq_means.values()), abs=1e-9) == 1.0
        assert freq_means[NORTH_SECTOR] == 1.0

        for month in range(1, 12):
            month_rows = result.filter(pl.col("month") == month)
            assert pytest.approx(month_rows["frequency"].sum(), abs=1e-9) == 1.0
