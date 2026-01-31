"""Wind extrapolation module for CleanMast."""

from .config import (
    ExtrapolateConfiguration,
    MastExtrapolateConfig,
    WindDirectionConfig,
    WindDirectionHeightConfig,
    WindDirectionReference,
    WindSpeedConfig,
    WindSpeedHeightConfig,
    WindSpeedReference,
    load_extrapolate_config,
)
from .recommend import (
    RecommendStrategy,
    Top3ConstantShearStrategy,
    get_strategy,
    list_strategies,
)
from .execute import execute_extrapolation, extrapolate_mast
from .shear import (
    calculate_shear_exponent,
    extrapolate_wind_direction,
    extrapolate_wind_speed,
    fit_shear_from_heights,
)

__all__ = [
    # Config
    "WindSpeedReference",
    "WindSpeedHeightConfig",
    "WindSpeedConfig",
    "WindDirectionReference",
    "WindDirectionHeightConfig",
    "WindDirectionConfig",
    "MastExtrapolateConfig",
    "ExtrapolateConfiguration",
    "load_extrapolate_config",
    # Recommend
    "RecommendStrategy",
    "Top3ConstantShearStrategy",
    "get_strategy",
    "list_strategies",
    # Shear
    "extrapolate_wind_speed",
    "calculate_shear_exponent",
    "fit_shear_from_heights",
    "extrapolate_wind_direction",
    # Execute
    "execute_extrapolation",
    "extrapolate_mast",
]
