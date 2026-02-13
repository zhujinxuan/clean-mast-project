"""Wind extrapolation recommend module.

Strategy-based configuration generation for vertical wind extrapolation.
"""

from .registry import RecommendStrategy, get_strategy, list_strategies, register_strategy

# Import strategies to register them
from .top3_constant_shear import Top3ConstantShearStrategy

__all__ = [
    "RecommendStrategy",
    "get_strategy",
    "list_strategies",
    "register_strategy",
    "Top3ConstantShearStrategy",
]
