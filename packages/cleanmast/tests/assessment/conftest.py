"""Fixtures for assessment tests."""

from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.entities.single_mast.daily_pattern import (
    SingleMastDailyPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.daily_power_pattern import (
    SingleMastDailyPowerPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_daily_power import (
    SingleMastMonthlyDailyPowerAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_daily_wind import (
    SingleMastMonthlyDailyWindAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_pattern import (
    SingleMastMonthlyPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_power_pattern import (
    SingleMastMonthlyPowerPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_intensity import (
    SingleMastTurbulenceIntensityAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_sector import (
    SingleMastTurbulenceSectorAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_summary import (
    SingleMastTurbulenceSummaryAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.vertical_profile import (
    SingleMastVerticalProfileAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.weibull_distribution import (
    SingleMastWeibullDistributionAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.weibull_multi import (
    SingleMastWeibullMultiHeightAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.weibull_parameters import (
    SingleMastWeibullParametersAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_frequency_table import (
    SingleMastWindFrequencyTableAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_power_frequency_table import (
    SingleMastWindPowerFrequencyTableAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_range_summary import (
    SingleMastWindRangeSummaryAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_rose import (
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_rose_grid import (
    SingleMastMonthlyWindRoseGridAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_shear_matrix import (
    SingleMastWindShearExponentAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_shear_table import (
    SingleMastWindShearTableAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects.schemas import (
    VerticalProfileSchema,
    WindShearSchema,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TemporalPatternSchema,
    TurbulenceSchema,
    TurbulenceSectorSchema,
    WeibullSchema,
    WindFrequencySchema,
    WindRoseSchema,
)


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    return tmp_path / "output"


@pytest.fixture
def sample_mast_meta() -> SingleMastMeta:
    return SingleMastMeta(
        mast_name="M01",
        air_density=1.225,
        caption="Test Caption",
        width="80%",
    )


@pytest.fixture
def sample_wind_rose_df() -> pl.DataFrame:
    sectors = list(range(16))
    sector_names = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                   "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

    data: dict[str, list[Any]] = {
        "month": [],
        "month_name": [],
        "sector": [],
        "sector_name": [],
        "height": [],
        "interpolation_marker": [],
        "frequency": [],
        "wind_power_density": [],
    }

    for month in [1, 2, 3]:
        month_name = f"{month}月"
        for height in [80.0, 120.0]:
            marker = "外推" if height > 100 else ""
            for i, (sector, name) in enumerate(zip(sectors, sector_names)):
                freq = 0.2 if i == 0 else 0.05
                power = 300.0 if i == 0 else 100.0

                data["month"].append(month)
                data["month_name"].append(month_name)
                data["sector"].append(sector)
                data["sector_name"].append(name)
                data["height"].append(height)
                data["interpolation_marker"].append(marker if marker else None)
                data["frequency"].append(freq)
                data["wind_power_density"].append(power)

    return pl.DataFrame(data)


@pytest.fixture
def wind_frequency_rose_atom(
    sample_wind_rose_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    return SingleMastMonthlyWindFrequencyRoseAtom.create(
        schema=WindRoseSchema,
        df=sample_wind_rose_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_power_rose_atom(
    sample_wind_rose_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    return SingleMastWindPowerRoseAtom.create(
        schema=WindRoseSchema,
        df=sample_wind_rose_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def sample_monthly_wind_df() -> pl.DataFrame:
    """Create sample monthly wind DataFrame using TemporalPatternSchema columns.

    The entity SingleMastMonthlyPatternAtom uses TemporalPatternSchema
    which has columns: timestamp, hour, month, wind_speed, wind_power,
    height, mean_speed, mean_power, interpolation_marker.
    """
    return pl.DataFrame({
        "timestamp": [datetime(2023, m, 15) for m in [1, 1, 2, 2, 3, 3]],
        "hour": [12] * 6,
        "month": [1, 1, 2, 2, 3, 3],
        "wind_speed": [None] * 6,
        "wind_power": [None] * 6,
        "height": [80.0, 120.0, 80.0, 120.0, 80.0, 120.0],
        "mean_speed": [5.2, 5.8, 5.5, 6.1, 6.0, 6.8],
        "mean_power": [150.5, 220.3, 180.2, 260.8, 200.5, 300.2],
        "interpolation_marker": [None, "外推", None, "外推", None, "外推"],
    })


@pytest.fixture
def sample_monthly_wind_power_df() -> pl.DataFrame:
    """Create sample monthly wind power DataFrame using TemporalPatternSchema columns.

    The entity SingleMastMonthlyPowerPatternAtom uses TemporalPatternSchema
    which has columns: timestamp, hour, month, wind_speed, wind_power,
    height, mean_speed, mean_power, interpolation_marker.
    """
    return pl.DataFrame({
        "timestamp": [datetime(2023, m, 15) for m in [1, 1, 2, 2, 3, 3]],
        "hour": [12] * 6,
        "month": [1, 1, 2, 2, 3, 3],
        "wind_speed": [None] * 6,
        "wind_power": [None] * 6,
        "height": [80.0, 120.0, 80.0, 120.0, 80.0, 120.0],
        "mean_speed": [5.2, 5.8, 5.5, 6.1, 6.0, 6.8],
        "mean_power": [150.5, 220.3, 180.2, 260.8, 200.5, 300.2],
        "interpolation_marker": [None, "外推", None, "外推", None, "外推"],
    })


@pytest.fixture
def monthly_wind_atom(
    sample_monthly_wind_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastMonthlyPatternAtom for testing."""
    return SingleMastMonthlyPatternAtom.create(
        schema=TemporalPatternSchema,
        df=sample_monthly_wind_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def monthly_wind_power_atom(
    sample_monthly_wind_power_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastMonthlyPowerPatternAtom for testing."""
    return SingleMastMonthlyPowerPatternAtom.create(
        schema=TemporalPatternSchema,
        df=sample_monthly_wind_power_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def turbulence_intensity_atom(
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastTurbulenceIntensityAtom for testing."""
    df = pl.DataFrame({
        "wind_speed_bin": [3, 5, 7, 9, 11, 13],
        "height": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
        "interpolation_marker": [None, None, None, None, None, None],
        "mean_ti": [0.18, 0.15, 0.12, 0.10, 0.09, 0.08],
        "std_ti": [0.03, 0.02, 0.02, 0.015, 0.01, 0.01],
        "representative_ti": [0.218, 0.176, 0.146, 0.119, 0.103, 0.093],
        "iec_category": ["B", "B", "A", "A", "A", "A"],
    })
    return SingleMastTurbulenceIntensityAtom.create(
        schema=TurbulenceSchema,
        df=df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def turbulence_sector_atom(
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastTurbulenceSectorAtom for testing."""
    sectors = list(range(16))
    sector_names = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                   "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    
    data: dict[str, list[Any]] = {
        "sector": [],
        "sector_name": [],
        "height": [],
        "interpolation_marker": [],
        "mean_ti": [],
        "representative_ti": [],
        "iec_category": [],
    }
    
    for height in [80.0, 120.0]:
        marker = "外推" if height > 100 else ""
        for sector, name in zip(sectors, sector_names):
            data["sector"].append(sector)
            data["sector_name"].append(name)
            data["height"].append(height)
            data["interpolation_marker"].append(marker if marker else None)
            data["mean_ti"].append(0.15 if sector == 0 else 0.12)
            data["representative_ti"].append(0.18 if sector == 0 else 0.15)
            data["iec_category"].append("B")
    
    return SingleMastTurbulenceSectorAtom.create(
        schema=TurbulenceSectorSchema,
        df=pl.DataFrame(data),
        meta=sample_mast_meta,
    )


@pytest.fixture
def turbulence_summary_atom(
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastTurbulenceSummaryAtom for testing."""
    df = pl.DataFrame({
        "wind_speed_bin": [3, 5, 7, 9, 11, 13, 3, 5, 7, 9, 11, 13],
        "height": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
                   120.0, 120.0, 120.0, 120.0, 120.0, 120.0],
        "interpolation_marker": [None, None, None, None, None, None,
                                "外推", "外推", "外推", "外推", "外推", "外推"],
        "mean_ti": [0.18, 0.15, 0.12, 0.10, 0.09, 0.08,
                    0.17, 0.14, 0.11, 0.09, 0.08, 0.07],
        "std_ti": [0.03, 0.02, 0.02, 0.015, 0.01, 0.01,
                   0.025, 0.02, 0.018, 0.014, 0.01, 0.009],
        "representative_ti": [0.218, 0.176, 0.146, 0.119, 0.103, 0.093,
                             0.202, 0.166, 0.133, 0.108, 0.093, 0.082],
        "iec_category": ["B", "B", "A", "A", "A", "A",
                        "B", "B", "A", "A", "A", "A"],
    })
    return SingleMastTurbulenceSummaryAtom.create(
        schema=TurbulenceSchema,
        df=df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def sample_weibull_df() -> pl.DataFrame:
    """Create sample Weibull DataFrame for testing."""
    import numpy as np
    
    bin_centers = np.arange(0.5, 30.5, 1.0).tolist()
    observed_density = [0.02 + 0.01 * np.sin(i) for i in range(len(bin_centers))]
    fitted_density = [0.02 + 0.008 * np.sin(i) for i in range(len(bin_centers))]
    
    return pl.DataFrame({
        "height": [80.0, 120.0],
        "interpolation_marker": [None, "外推"],
        "shape_k": [2.1, 2.3],
        "scale_c": [7.5, 8.2],
        "mean_speed": [6.8, 7.5],
        "bin_centers": [bin_centers, bin_centers],
        "observed_density": [observed_density, observed_density],
        "fitted_density": [fitted_density, fitted_density],
    })


@pytest.fixture
def weibull_distribution_atom(
    sample_weibull_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastWeibullDistributionAtom for testing."""
    return SingleMastWeibullDistributionAtom.create(
        schema=WeibullSchema,
        df=sample_weibull_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def weibull_parameters_atom(
    sample_weibull_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastWeibullParametersAtom for testing."""
    return SingleMastWeibullParametersAtom.create(
        schema=WeibullSchema,
        df=sample_weibull_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def weibull_multi_atom(
    sample_weibull_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastWeibullMultiHeightAtom for testing."""
    return SingleMastWeibullMultiHeightAtom.create(
        schema=WeibullSchema,
        df=sample_weibull_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def vertical_profile_atom(
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastVerticalProfileAtom for testing."""
    df = pl.DataFrame({
        "height": [50.0, 80.0, 100.0, 120.0],
        "interpolation_marker": [None, None, None, "外推"],
        "wind_speed_mean": [5.2, 6.1, 6.8, 7.2],
        "wind_speed_std": [1.8, 2.0, 2.1, 2.2],
        "alpha": [0.15, 0.15, 0.15, 0.15],
        "r_squared": [0.98, 0.98, 0.98, 0.98],
    })
    return SingleMastVerticalProfileAtom.create(
        schema=VerticalProfileSchema,
        df=df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_shear_table_atom(
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastWindShearTableAtom for testing."""
    df = pl.DataFrame({
        "from_height": [50.0, 50.0, 80.0],
        "to_height": [80.0, 120.0, 120.0],
        "alpha_mean": [0.15, 0.14, 0.13],
        "alpha_std": [0.03, 0.025, 0.02],
        "alpha_min": [0.08, 0.07, 0.06],
        "alpha_max": [0.25, 0.22, 0.20],
    })
    return SingleMastWindShearTableAtom.create(
        schema=WindShearSchema,
        df=df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_shear_matrix_atom(
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastWindShearExponentAtom for testing."""
    df = pl.DataFrame({
        "from_height": [50.0, 50.0, 80.0],
        "to_height": [80.0, 120.0, 120.0],
        "alpha_mean": [0.15, 0.14, 0.13],
        "alpha_std": [0.03, 0.025, 0.02],
        "alpha_min": [0.08, 0.07, 0.06],
        "alpha_max": [0.25, 0.22, 0.20],
    })
    return SingleMastWindShearExponentAtom.create(
        schema=WindShearSchema,
        df=df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def sample_wind_frequency_df() -> pl.DataFrame:
    """Create sample wind frequency DataFrame for testing."""
    bins = list(range(0, 29))
    heights = [80.0, 120.0]
    
    data: dict[str, list[Any]] = {
        "height": [],
        "interpolation_marker": [],
        "bin_start": [],
        "bin_end": [],
        "bin_center": [],
        "frequency": [],
        "occurrence_hours": [],
        "power_frequency": [],
        "power_hours": [],
    }
    
    for height in heights:
        marker = "外推" if height > 100 else None
        for bin_start in bins:
            bin_end = bin_start + 1 if bin_start < 28 else bin_start + 10
            bin_center = (bin_start + bin_end) / 2
            freq = 0.03 if bin_start < 10 else 0.01
            power_freq = 0.001 if bin_start < 5 else (0.05 if 5 <= bin_start < 15 else 0.01)
            
            data["height"].append(height)
            data["interpolation_marker"].append(marker)
            data["bin_start"].append(float(bin_start))
            data["bin_end"].append(float(bin_end))
            data["bin_center"].append(bin_center)
            data["frequency"].append(freq)
            data["occurrence_hours"].append(freq * 8760)
            data["power_frequency"].append(power_freq)
            data["power_hours"].append(power_freq * 8760)
    
    return pl.DataFrame(data)


@pytest.fixture
def wind_frequency_table_atom(
    sample_wind_frequency_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastWindFrequencyTableAtom for testing."""
    return SingleMastWindFrequencyTableAtom.create(
        schema=WindFrequencySchema,
        df=sample_wind_frequency_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_power_frequency_table_atom(
    sample_wind_frequency_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastWindPowerFrequencyTableAtom for testing."""
    return SingleMastWindPowerFrequencyTableAtom.create(
        schema=WindFrequencySchema,
        df=sample_wind_frequency_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_range_summary_atom(
    sample_wind_frequency_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastWindRangeSummaryAtom for testing."""
    return SingleMastWindRangeSummaryAtom.create(
        schema=WindFrequencySchema,
        df=sample_wind_frequency_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_rose_grid_atom(
    sample_wind_rose_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastMonthlyWindRoseGridAtom for testing."""
    return SingleMastMonthlyWindRoseGridAtom.create(
        schema=WindRoseSchema,
        df=sample_wind_rose_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def sample_temporal_pattern_df() -> pl.DataFrame:
    """Create sample temporal pattern DataFrame for testing."""
    heights = [80.0, 120.0]
    hours = list(range(24))
    
    data: dict[str, list[Any]] = {
        "timestamp": [],
        "hour": [],
        "month": [],
        "wind_speed": [],
        "wind_power": [],
        "height": [],
        "mean_speed": [],
        "mean_power": [],
        "interpolation_marker": [],
    }
    
    for month in [1, 2, 3]:
        for height in heights:
            marker = "外推" if height > 100 else None
            for hour in hours:
                data["timestamp"].append(datetime(2023, month, 15, hour))
                data["hour"].append(hour)
                data["month"].append(month)
                data["wind_speed"].append(5.0 + 0.5 * (hour % 12) if hour < 12 else 5.0 + 0.5 * (24 - hour))
                data["wind_power"].append(150.0 + 10.0 * (hour % 12) if hour < 12 else 150.0 + 10.0 * (24 - hour))
                data["height"].append(height)
                data["mean_speed"].append(5.5 + 0.3 * (height / 100))
                data["mean_power"].append(180.0 + 20.0 * (height / 100))
                data["interpolation_marker"].append(marker)
    
    return pl.DataFrame(data)


@pytest.fixture
def daily_pattern_atom(
    sample_temporal_pattern_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastDailyPatternAtom for testing."""
    return SingleMastDailyPatternAtom.create(
        schema=TemporalPatternSchema,
        df=sample_temporal_pattern_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def daily_power_pattern_atom(
    sample_temporal_pattern_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastDailyPowerPatternAtom for testing."""
    return SingleMastDailyPowerPatternAtom.create(
        schema=TemporalPatternSchema,
        df=sample_temporal_pattern_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def monthly_daily_wind_atom(
    sample_temporal_pattern_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastMonthlyDailyWindAtom for testing."""
    return SingleMastMonthlyDailyWindAtom.create(
        schema=TemporalPatternSchema,
        df=sample_temporal_pattern_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def monthly_daily_power_atom(
    sample_temporal_pattern_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastMonthlyDailyPowerAtom for testing."""
    return SingleMastMonthlyDailyPowerAtom.create(
        schema=TemporalPatternSchema,
        df=sample_temporal_pattern_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def wind_power_rose_atom_null_power(
    sample_wind_rose_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> Any:
    """Create a SingleMastWindPowerRoseAtom with null power data for testing."""
    # Create DataFrame with null power density
    df_null_power = sample_wind_rose_df.with_columns(
        pl.lit(None).alias("wind_power_density")
    )
    return SingleMastWindPowerRoseAtom.create(
        schema=WindRoseSchema,
        df=df_null_power,
        meta=sample_mast_meta,
    )


@pytest.fixture
def all_atoms(
    wind_frequency_rose_atom: Any,
    wind_power_rose_atom: Any,
    monthly_wind_atom: Any,
    monthly_wind_power_atom: Any,
    turbulence_intensity_atom: Any,
    turbulence_sector_atom: Any,
    turbulence_summary_atom: Any,
    weibull_distribution_atom: Any,
    weibull_parameters_atom: Any,
    weibull_multi_atom: Any,
    vertical_profile_atom: Any,
    wind_shear_table_atom: Any,
    wind_shear_matrix_atom: Any,
    wind_frequency_table_atom: Any,
    wind_power_frequency_table_atom: Any,
    wind_range_summary_atom: Any,
    wind_rose_grid_atom: Any,
    daily_pattern_atom: Any,
    daily_power_pattern_atom: Any,
    monthly_daily_wind_atom: Any,
    monthly_daily_power_atom: Any,
) -> list[Any]:
    """Create a list of all atom fixtures for testing."""
    return [
        wind_frequency_rose_atom,
        wind_power_rose_atom,
        monthly_wind_atom,
        monthly_wind_power_atom,
        turbulence_intensity_atom,
        turbulence_sector_atom,
        turbulence_summary_atom,
        weibull_distribution_atom,
        weibull_parameters_atom,
        weibull_multi_atom,
        vertical_profile_atom,
        wind_shear_table_atom,
        wind_shear_matrix_atom,
        wind_frequency_table_atom,
        wind_power_frequency_table_atom,
        wind_range_summary_atom,
        wind_rose_grid_atom,
        daily_pattern_atom,
        daily_power_pattern_atom,
        monthly_daily_wind_atom,
        monthly_daily_power_atom,
    ]
